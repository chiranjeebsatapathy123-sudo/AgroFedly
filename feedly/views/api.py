from ..decorators import _organization_required, _manager_required, require_org_role
import json
import os
from datetime import date, timedelta, datetime
from functools import wraps
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Sum, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from ..forms import DeliveryForm, MemberForm, OrganizationForm, RedistributionForm, SurplusFoodForm
from ..models import DemandForecast, Delivery, MealRecord, Organization, OrganizationMember, Recipient, Redistribution, SurplusFood, IoTTemperatureReading, Ingredient, OrganizationImpact
User = get_user_model()
from ..services.forecasting import DemandForecastingPipeline
from ..forms import PostMealRecordForm
from ..models import AgriculturalProduce, ProcessingRecord, AgriculturalSupplyRequest
from ..forms import AgriculturalProduceForm, ProcessingRecordForm, AgriculturalSupplyRequestForm
from django.db.models import Sum
from ..models import AgriculturalProduce, ProcessingRecord, AgriculturalSupplyRequest
from ..forms import AgriculturalProduceForm, ProcessingRecordForm, AgriculturalSupplyRequestForm
from django.db.models import Sum
from ..models import BuyerDemand, SupplyMatch
from ..forms import BuyerDemandForm
import difflib
from ..models import CropMarketTrend, WeatherAdvisory, AgriculturalShipment, QualityInspection, LedgerTransaction
from ..forms import QualityInspectionForm
import json
from django.utils import timezone
from ..forms import VolunteerProfileForm
from ..models import VolunteerProfile, OrganizationImpact
import io
from django.http import FileResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from ..copilot import generate_copilot_response
import qrcode
from django.http import HttpResponse

from django.db import connection
from django.conf import settings

def health_liveness(request):
    """
    Basic liveness check. Returns 200 OK if the application is running.
    """
    return JsonResponse({'status': 'ok'})

def health_readiness(request):
    """
    Readiness check. Verifies database and external dependencies.
    """
    health = {'status': 'ready'}
    status_code = 200
    
    # Check Database
    try:
        connection.ensure_connection()
        health['database'] = 'ok'
    except Exception as e:
        health['status'] = 'error'
        health['database'] = 'error'
        status_code = 503

    # Check Redis
    if hasattr(settings, 'CHANNEL_LAYERS') and 'default' in settings.CHANNEL_LAYERS:
        try:
            redis_url = settings.CHANNEL_LAYERS['default'].get('CONFIG', {}).get('hosts', [None])[0]
            if redis_url:
                import redis
                r = redis.from_url(redis_url, socket_timeout=1)
                r.ping()
                health['redis'] = 'ok'
            else:
                health['redis'] = 'ok (in-memory)'
        except Exception as e:
            health['status'] = 'error'
            health['redis'] = 'error'
            status_code = 503
            
    return JsonResponse(health, status=status_code)

def _weather(city):
    key = getattr(settings, 'WEATHER_API_KEY', '')
    if not city or not key:
        return None
    try:
        import requests
        response = requests.get('https://api.openweathermap.org/data/2.5/weather', params={'q': city, 'appid': key, 'units': 'metric'}, timeout=8)
        response.raise_for_status()
        data = response.json()
        return {'temperature': float(data['main']['temp']), 'humidity': float(data['main'].get('humidity', 70)), 'rainfall': float(data.get('rain', {}).get('1h', 0)), 'weather': data['weather'][0]['description'], 'is_live': True}
    except Exception:
        return None

# Legacy _predict removed in favor of DemandForecastingPipeline
@login_required
def predict_demand(request):
    result = None
    weather = None
    error = None
    today_erp = MealRecord.objects.filter(date=date.today(), data_source='ERP').first()
    default_attendance = today_erp.attendance if today_erp else 0
    if request.method == 'POST':
        try:
            attendance = int(request.POST.get('attendance', 0))
            holiday = int(request.POST.get('holiday', 0))
            exam_day = int(request.POST.get('exam_day', 0))
            event_flag = int(request.POST.get('event_flag', 0))
            city = request.POST.get('city', '').strip()
            if attendance < 0:
                raise ValueError('Attendance cannot be negative.')
            weather = _weather(city) if city else None
            if city and (not weather) and getattr(settings, 'WEATHER_API_KEY', ''):
                weather = {'temperature': 25, 'humidity': 70, 'rainfall': 0}
            humidity = weather['humidity'] if weather else 70
            temperature = weather['temperature'] if weather else 25
            rainfall = weather['rainfall'] if weather else 0
            org = request.user.organization_memberships.first().organization if request.user.organization_memberships.exists() else None
            pipeline = DemandForecastingPipeline(org)
            # This handles creating the model internally.
            forecast_obj = pipeline.predict_demand(
                attendance=attendance, temperature=temperature, rainfall=rainfall, 
                holiday=holiday, humidity=humidity, exam_day=exam_day, event_flag=event_flag
            )
            # Create a result dictionary for the template to render
            result = {
                'prediction': forecast_obj.predicted_demand,
                'recommended': forecast_obj.recommended_preparation,
                'lower': forecast_obj.lower_bound,
                'upper': forecast_obj.upper_bound,
                'confidence': forecast_obj.confidence,
                'expected_surplus': forecast_obj.expected_surplus,
                'risk': forecast_obj.waste_risk,
                'model_name': forecast_obj.model_name
            }
            messages.success(request, 'AI forecast saved successfully.')
            messages.success(request, 'AI forecast saved successfully.')
        except (ValueError, TypeError) as exc:
            error = str(exc)
            
    # Calculate Model Performance Metrics (MAE, RMSE)
    import math
    past_forecasts = DemandForecast.objects.filter(date__lt=date.today()).order_by('-date')[:30]
    past_meals = {m.date: m.meals_consumed for m in MealRecord.objects.filter(date__in=[f.date for f in past_forecasts]).exclude(data_source='ERP')}
    
    errors = []
    for f in past_forecasts:
        actual = past_meals.get(f.date)
        if actual is not None and actual > 0:
            errors.append(abs(f.predicted_demand - actual))
            
    mae = sum(errors) / len(errors) if errors else 0
    rmse = math.sqrt(sum(e**2 for e in errors) / len(errors)) if errors else 0
    drift_warning = mae > 20  # Threshold for warning
    model_metrics = {'mae': round(mae, 1), 'rmse': round(rmse, 1), 'drift_warning': drift_warning, 'samples': len(errors)}
    
    produce_requirements = []
    if result:
        ingredients = Ingredient.objects.filter(is_active=True)
        for ingredient in ingredients:
            produce_requirements.append({'name': ingredient.name, 'unit': ingredient.unit, 'required': round(result['prediction'] * ingredient.quantity_per_meal, 2), 'recommended': round(result['recommended'] * ingredient.quantity_per_meal, 2), 'buffer': round((result['recommended'] - result['prediction']) * ingredient.quantity_per_meal, 2)})
    return render(request, 'predict.html', {'result': result, 'weather': weather, 'error': error, 'model_name': "AgroFedly AI 2.0", 'default_attendance': default_attendance, 'produce_requirements': produce_requirements, 'model_metrics': model_metrics})

@login_required
def forecast_7_days(request):
    forecasts = []
    if request.method == 'POST':
        try:
            attendance = int(request.POST.get('attendance', 0))
            holiday = int(request.POST.get('holiday', 0))
            if attendance <= 0:
                raise ValueError('Attendance must be greater than zero.')
            scenario_forecasts = []
            org = request.user.organization_memberships.first().organization if request.user.organization_memberships.exists() else None
            pipeline = DemandForecastingPipeline(org)
            for offset in range(7):
                target = date.today() + timedelta(days=offset)
                
                # Base Model
                base_forecast = pipeline.predict_demand(
                    attendance=int(round(attendance * (0.82 if target.weekday() >= 5 else 1))),
                    holiday=int(target.weekday() >= 5),
                    target_date=target
                )
                base_item = {
                    'date': target, 'prediction': base_forecast.predicted_demand, 'recommended': base_forecast.recommended_preparation, 'risk': base_forecast.waste_risk, 'expected_surplus': base_forecast.expected_surplus
                }
                
                # Custom Scenario
                scenario_forecast = pipeline.predict_demand(
                    attendance=int(round(attendance * (0.82 if target.weekday() >= 5 else 1))),
                    holiday=holiday if offset == 0 else int(target.weekday() >= 5),
                    target_date=target
                )
                scenario_item = {
                    'date': target, 'prediction': scenario_forecast.predicted_demand, 'recommended': scenario_forecast.recommended_preparation, 'risk': scenario_forecast.waste_risk, 'expected_surplus': scenario_forecast.expected_surplus
                }
                
                forecasts.append(base_item)
                scenario_forecasts.append(scenario_item)
                
        except (ValueError, TypeError) as exc:
            messages.error(request, str(exc))
    return render(request, 'forecast.html', {'forecasts': forecasts, 'scenario_forecasts': scenario_forecasts if request.method == 'POST' else None, 'model_name': "AgroFedly AI 2.0"})

@login_required
def weather_data(request):
    """Return live weather for the requested city with mock fallback."""
    city = request.GET.get('city', '').strip()
    if not city:
        return JsonResponse({'error': 'Please enter a city name.', 'is_live': False}, status=400)
    weather = _weather(city)
    if weather is None:
        return JsonResponse({
            'city': city,
            'temperature': 28.5,
            'humidity': 60.0,
            'rainfall': 0.0,
            'weather': 'Simulated Clear Sky',
            'is_live': False,
            'source': 'Mock Data (API Unavailable)',
            'warning': 'OpenWeather API is unavailable or not configured. Using simulated data.'
        }, status=200)
    return JsonResponse({'city': city, 'temperature': weather['temperature'], 'humidity': weather['humidity'], 'rainfall': weather['rainfall'], 'weather': weather['weather'], 'is_live': True, 'source': 'OpenWeather'})

def require_api_key(view_func):
    def _wrapped_view(request, *args, **kwargs):
        api_key = request.headers.get('Authorization') or request.headers.get('X-API-Key')
        if getattr(settings, 'DEBUG', False) and not api_key:
             pass # Allow in debug if not provided, or strictly enforce it? The prompt says "must not be publicly writable. Protect with proper authentication."
        if not api_key or (api_key.replace("Bearer ", "") != getattr(settings, 'API_KEY', 'default-insecure-api-key-for-dev') and api_key != getattr(settings, 'API_KEY', '')):
            return JsonResponse({'error': 'Unauthorized: Invalid or missing API Key'}, status=401)
        return view_func(request, *args, **kwargs)
    return _wrapped_view

@login_required
def api_notifications(request):
    """Fetch unread notifications for the user."""
    from ..models import Notification
    
    # Get user specific or org specific notifications
    if hasattr(request.user, 'profile') and request.user.profile.role == 'FPO':
        org_member = request.user.organization_memberships.first()
        if org_member:
            notifs = Notification.objects.filter(organization=org_member.organization, is_read=False).order_by('-created_at')[:10]
        else:
            notifs = Notification.objects.filter(user=request.user, is_read=False).order_by('-created_at')[:10]
    else:
        notifs = Notification.objects.filter(user=request.user, is_read=False).order_by('-created_at')[:10]
        
    data = [{'id': n.id, 'type': n.notification_type, 'message': n.message, 'time': n.created_at.isoformat()} for n in notifs]
    return JsonResponse({'status': 'success', 'notifications': data})

@login_required
@csrf_exempt
def api_notifications_read(request):
    """Mark notifications as read."""
    if request.method == 'POST':
        from ..models import Notification
        try:
            body = json.loads(request.body)
            notif_id = body.get('id')
            if notif_id:
                notif = Notification.objects.filter(id=notif_id).first()
                if notif:
                    notif.is_read = True
                    notif.save()
            else:
                # Mark all as read
                Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    return JsonResponse({'status': 'error'}, status=405)

@require_api_key
def api_erp_attendance(request):
    """External API endpoint for ERP to push attendance data."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST allowed'}, status=405)
    try:
        data = json.loads(request.body)
        attendance = int(data.get('attendance', 0))
        date_str = data.get('date')
        if attendance < 0:
            return JsonResponse({'error': 'Attendance cannot be negative'}, status=400)
        record_date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else timezone.localdate()
        record, created = MealRecord.objects.update_or_create(date=record_date, data_source='ERP', defaults={'attendance': attendance, 'meals_prepared': 0, 'meals_consumed': 0})
        return JsonResponse({'status': 'success', 'message': 'ERP attendance recorded', 'attendance': attendance, 'date': str(record_date)})
    except (ValueError, TypeError, json.JSONDecodeError) as e:
        return JsonResponse({'error': str(e)}, status=400)

@require_api_key
def api_iot_temperature(request):
    """External API endpoint for ESP32/IoT to push temperature data."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST allowed'}, status=405)
    try:
        data = json.loads(request.body)
        temperature = float(data.get('temperature'))
        food_name = data.get('food_name', 'IoT Monitored Food')[:100]
        sensor_name = data.get('sensor_name', 'IoT Sensor')[:100]
        location = data.get('location', '')[:150]
        safe = -1 <= temperature <= 5
        status = 'SAFE' if safe else 'ALERT'
        reading = IoTTemperatureReading.objects.create(sensor_name=sensor_name, food_name=food_name, temperature=temperature, location=location, status=status)
        return JsonResponse({'status': 'success', 'id': reading.id, 'temperature': temperature, 'food_name': food_name, 'safety_status': status})
    except (ValueError, TypeError, json.JSONDecodeError) as e:
        return JsonResponse({'error': str(e)}, status=400)

def api_iot_live_stream(request):
    """Simulates live temperature stream for active shipments"""
    active_shipments = AgriculturalShipment.objects.filter(status='IN_TRANSIT')
    data = []
    for shipment in active_shipments:
        current = shipment.current_temperature or 4.0
        fluctuation = 0.0
        new_temp = round(current + fluctuation, 1)
        shipment.current_temperature = new_temp
        shipment.save(update_fields=['current_temperature'])
        data.append({'tracking_code': shipment.tracking_code, 'temperature': new_temp, 'status': 'Warning' if new_temp > 6.0 or new_temp < 0.0 else 'Normal'})
    return JsonResponse({'status': 'success', 'data': data})

@_organization_required
def copilot_chat(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_message = data.get('message', '').strip().lower()
            context = data.get('context', '/')
            if not user_message:
                return JsonResponse({'error': 'No message provided'}, status=400)
                
            from feedly.models import AIChatHistory
            from feedly.ai.advisor import get_copilot_response
            
            # Save user message
            AIChatHistory.objects.create(
                user=request.user,
                message_role='USER',
                content=user_message,
                context_used={'url_context': context}
            )
                
            # Hardcoded NLP rules for Demo workflows (Phase 19)
            if "pause surplus alerts" in user_message or "pause alerts" in user_message:
                ai_response = {
                    'type': 'action_preview',
                    'action': 'pause_surplus_alerts',
                    'preview': {
                        'Automation': 'Surplus Alerts',
                        'Current': 'Enabled',
                        'New': 'Paused',
                        'Impact': 'You may stop receiving surplus alerts.'
                    }
                }
                AIChatHistory.objects.create(user=request.user, message_role='AI', content=json.dumps(ai_response))
                return JsonResponse(ai_response)
            
            # Phase 4 Advisor
            ai_response = get_copilot_response(request.user, user_message, context)
            
            # If the response is a JSON string (e.g. for navigation), parse it
            try:
                if isinstance(ai_response, str) and ai_response.strip().startswith('{'):
                    parsed = json.loads(ai_response)
                    AIChatHistory.objects.create(user=request.user, message_role='AI', content=ai_response)
                    return JsonResponse(parsed)
            except json.JSONDecodeError:
                pass
                
            AIChatHistory.objects.create(user=request.user, message_role='AI', content=ai_response)
            return JsonResponse({'response': ai_response})
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
    return JsonResponse({'error': 'Method not allowed'}, status=405)

@login_required
def api_global_search(request):
    """Global search endpoint for Command Palette (Ctrl+K) with NLP support."""
    q = request.GET.get('q', '').strip()
    if not q:
        return JsonResponse({'results': []})
        
    results = []
    org_member = request.user.organization_memberships.filter(is_active=True).first()
    org = org_member.organization if org_member else None
    
    q_lower = q.lower()
    
    # NLP Intent Detection
    intent = "search"
    if any(verb in q_lower for verb in ["go to", "open", "show me", "navigate to"]):
        intent = "navigate"
    elif any(verb in q_lower for verb in ["where is", "track", "find delivery"]):
        intent = "track"
        
    # 1. Search Deliveries
    deliveries = Delivery.objects.filter(
        Q(tracking_code__icontains=q) | Q(food_name__icontains=q)
    )
    if org:
        deliveries = deliveries.filter(Q(sender=org) | Q(receiver=org))
        
    for d in deliveriesif not (getattr(request.user, 'is_superuser', False) or getattr(request.user, 'profile', None) and getattr(request.user.profile, 'role', '') in ['SUPER_ADMIN', 'ADMIN']) and request.membership.role not in [:5]:
        results.append({
            'title': f'Delivery #{d.tracking_code}',
            'subtitle': f'{d.food_name} - {d.get_status_display()}',
            'url': f'/deliveries/{d.id}/',
            'type': 'Delivery' if intent != 'track' else 'Tracking Result',
            'icon': '📦' if intent != 'track' else '📍'
        })
        
    # 2. Search Surplus Food
    surplus = SurplusFood.objects.filter(food_name__icontains=q)
    if org:
        surplus = surplus.filter(organization=org)
        
    for s in surplusif not (getattr(request.user, 'is_superuser', False) or getattr(request.user, 'profile', None) and getattr(request.user.profile, 'role', '') in ['SUPER_ADMIN', 'ADMIN']) and request.membership.role not in [:5]:
        results.append({
            'title': s.food_name,
            'subtitle': f'{s.quantity} units - {s.get_status_display()}',
            'url': f'/surplus/',
            'type': 'Surplus',
            'icon': '🍎'
        })
        
    # 3. Search Users / Team (If Admin)
    if org:
        members = OrganizationMember.objects.filter(
            organization=org,
            user__username__icontains=q
        ).select_related('user')
        for m in membersif not (getattr(request.user, 'is_superuser', False) or getattr(request.user, 'profile', None) and getattr(request.user.profile, 'role', '') in ['SUPER_ADMIN', 'ADMIN']) and request.membership.role not in [:3]:
            results.append({
                'title': m.user.username,
                'subtitle': m.get_role_display(),
                'url': '/organization/',
                'type': 'Team',
                'icon': '👤'
            })
            
    # 4. Search Farms, Fields, Crops
    from ..models import Farm, Field, Crop
    if org:
        farms = Farm.objects.filter(organization=org, name__icontains=q)
        for f in farmsif not (getattr(request.user, 'is_superuser', False) or getattr(request.user, 'profile', None) and getattr(request.user.profile, 'role', '') in ['SUPER_ADMIN', 'ADMIN']) and request.membership.role not in [:3]:
            results.append({
                'title': f.name,
                'subtitle': f'{f.location}',
                'url': '/agriculture/farms/',
                'type': 'Farm',
                'icon': '🚜'
            })
            
        fields = Field.objects.filter(farm__organization=org, name__icontains=q).select_related('farm')
        for f in fieldsif not (getattr(request.user, 'is_superuser', False) or getattr(request.user, 'profile', None) and getattr(request.user.profile, 'role', '') in ['SUPER_ADMIN', 'ADMIN']) and request.membership.role not in [:3]:
            results.append({
                'title': f.name,
                'subtitle': f'Farm: {f.farm.name}',
                'url': '/agriculture/fields/',
                'type': 'Field',
                'icon': '🌱'
            })
            
        crops = Crop.objects.filter(field__farm__organization=org, name__icontains=q)
        for c in cropsif not (getattr(request.user, 'is_superuser', False) or getattr(request.user, 'profile', None) and getattr(request.user.profile, 'role', '') in ['SUPER_ADMIN', 'ADMIN']) and request.membership.role not in [:3]:
            results.append({
                'title': c.name,
                'subtitle': f'Variety: {c.variety}',
                'url': '/agriculture/calendar/',
                'type': 'Crop',
                'icon': '🌾'
            })
            
    # 4. Pages (Static commands & NLP Navigation)
    pages = [
        {'title': 'Dashboard', 'url': '/dashboard/', 'keywords': ['home', 'dashboard', 'start', 'overview'], 'icon': '📊'},
        {'title': 'Intelligence Center', 'url': '/intelligence/', 'keywords': ['ai', 'intelligence', 'metrics', 'brain'], 'icon': '🧠'},
        {'title': 'Redistribute Surplus', 'url': '/surplus/', 'keywords': ['redistribute', 'donate', 'give', 'surplus'], 'icon': '🤝'},
        {'title': 'Live Deliveries', 'url': '/deliveries/', 'keywords': ['delivery', 'logistics', 'map'], 'icon': '🚚'},
        {'title': 'Agriculture Command', 'url': '/agriculture/skyview/', 'keywords': ['farm', 'agriculture', 'skyview'], 'icon': '🌾'}
    ]
    
    for p in pages:
        if q_lower in p['title'].lower() or any(k in q_lower for k in p['keywords']):
            results.append({
                'title': p['title'],
                'subtitle': 'AI Page Navigation' if intent == 'navigate' else 'Page Navigation',
                'url': p['url'],
                'type': 'Navigation',
                'icon': p['icon']
            })

    # Sort results to put NLP intent matches first
    if intent == 'navigate':
        results.sort(key=lambda x: 0 if x['type'] == 'Navigation' else 1)
    elif intent == 'track':
        results.sort(key=lambda x: 0 if x['type'] == 'Tracking Result' else 1)

    return JsonResponse({'results': results})

@login_required
def api_ai_scenario(request):
    """What-If Simulator 2.0 Backend"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    try:
        data = json.loads(request.body)
        attendance = int(data.get('attendance', 0))
        temperature = float(data.get('temperature', 25.0))
        rainfall = float(data.get('rainfall', 0.0))
        production = int(data.get('production', 0))
        
        org = request.user.organization_memberships.first().organization if request.user.organization_memberships.exists() else None
        pipeline = DemandForecastingPipeline(org)
        
        # Calculate base using pipeline
        forecast_obj = pipeline.predict_demand(attendance=attendance, temperature=temperature, rainfall=rainfall)
        
        # Overlay user custom production vs AI recommended
        simulated_surplus = max(0, production - forecast_obj.predicted_demand)
        ratio = simulated_surplus / max(production, 1)
        risk = 'HIGH' if ratio >= 0.12 or simulated_surplus >= 80 else 'MEDIUM' if ratio >= 0.05 or simulated_surplus >= 30 else 'LOW'
        
        return JsonResponse({
            'success': True,
            'prediction': forecast_obj.predicted_demand,
            'simulated_surplus': simulated_surplus,
            'risk': risk,
            'confidence': forecast_obj.confidence
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@login_required
def api_ai_action_preview(request):
    """Preview consequences before applying action"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    try:
        data = json.loads(request.body)
        action_type = data.get('action_type')
        
        preview = {
            'action': action_type,
            'current': 'Unknown',
            'suggested': 'Unknown',
            'difference': 'N/A',
            'estimated_effect': [],
            'affected': 'Unknown'
        }
        
        if action_type == 'adjust_production':
            current = int(data.get('current', 0))
            suggested = int(data.get('suggested', 0))
            diff = suggested - current
            
            preview['current'] = f"{current} units"
            preview['suggested'] = f"{suggested} units"
            preview['difference'] = f"{diff} units"
            preview['estimated_effect'] = [
                f"Surplus reduction: {abs(diff)} units",
                f"Estimated cost change: ₹{abs(diff) * 35}"
            ]
            preview['affected'] = "Today's Production Plan"
            
        return JsonResponse({'success': True, 'preview': preview})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
def api_auth_me(request):
    """Phase 44: Returns the user's authenticated context."""
    user = request.user
    profile = getattr(user, 'profile', None)
    
    from feedly.services.permissions import get_permitted_workspaces, get_default_workspace
    permitted = list(get_permitted_workspaces(user))
    
    membership = OrganizationMember.objects.filter(user=user, is_active=True).first()
    org = membership.organization if membership else None
    
    data = {
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'account_status': profile.account_status if profile else 'UNKNOWN',
        'role': profile.role if profile else 'UNKNOWN',
        'onboarding_completed': profile.onboarding_completed if profile else False,
        'active_workspace': request.session.get('active_workspace'),
        'default_workspace': get_default_workspace(user),
        'permitted_workspaces': permitted,
        'organization': {
            'id': org.id,
            'name': org.name,
            'type': org.organization_type
        } if org else None
    }
    
    return JsonResponse(data)
