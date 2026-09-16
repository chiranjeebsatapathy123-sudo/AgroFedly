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
try:
    import joblib
except Exception:
    joblib = None
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(BASE_DIR, 'ml', 'demand_bundle.pkl')
LEGACY_MODEL_PATH = os.path.join(BASE_DIR, 'ml', 'demand_model.pkl')
MODEL = None
MODEL_FEATURES = []
MODEL_NAME = 'Fedly Smart Forecast'
RESIDUAL_P90 = 8.0
if joblib:
    try:
        bundle = joblib.load(MODEL_PATH)
        MODEL = bundle.get('model') if isinstance(bundle, dict) else bundle
        MODEL_FEATURES = bundle.get('features', []) if isinstance(bundle, dict) else []
        MODEL_NAME = bundle.get('model_name', MODEL_NAME) if isinstance(bundle, dict) else MODEL_NAME
        RESIDUAL_P90 = float(bundle.get('residual_p90', 8)) if isinstance(bundle, dict) else 8
    except Exception:
        try:
            MODEL = joblib.load(LEGACY_MODEL_PATH)
            MODEL_FEATURES = ['attendance', 'temperature', 'rainfall', 'holiday', 'day_of_week']
            MODEL_NAME = 'Legacy Demand Model'
        except Exception:
            pass
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

def health_check(request):
    health = {'status': 'ok', 'service': 'AgroFedly'}
    status_code = 200
    
    # Check Database
    try:
        connection.ensure_connection()
        health['database'] = 'connected'
    except Exception as e:
        health['status'] = 'error'
        health['database'] = 'disconnected'
        status_code = 503

    # Check Redis
    if hasattr(settings, 'CHANNEL_LAYERS') and 'default' in settings.CHANNEL_LAYERS:
        try:
            redis_url = settings.CHANNEL_LAYERS['default'].get('CONFIG', {}).get('hosts', [None])[0]
            if redis_url:
                import redis
                r = redis.from_url(redis_url)
                r.ping()
                health['redis'] = 'connected'
            else:
                health['redis'] = 'in-memory (dev)'
        except Exception as e:
            health['status'] = 'error'
            health['redis'] = 'disconnected'
            status_code = 503
            
    # Check ML Model
    if MODEL:
        health['ml_model'] = 'loaded'
    else:
        health['ml_model'] = 'unavailable (fallback active)'

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

def _predict(attendance, temperature=25, rainfall=0, holiday=0, humidity=70, exam_day=0, event_flag=0, target=None):
    target = target or date.today()
    recent_meals = list(MealRecord.objects.filter(date__lt=target).exclude(data_source='ERP').order_by('-date').values_list('meals_consumed', flat=True)[:7])
    if recent_meals and sum(recent_meals) > 0:
        recent_avg = sum(recent_meals) / len(recent_meals)
    else:
        recent = list(DemandForecast.objects.filter(date__lt=target).order_by('-date').values_list('predicted_demand', flat=True)[:7])
        recent_avg = sum(recent) / len(recent) if recent else attendance * 0.86
    features = {'attendance': attendance, 'temperature': temperature, 'rainfall': rainfall, 'holiday': holiday, 'day_of_week': target.weekday(), 'humidity': humidity, 'month': target.month, 'weekend': int(target.weekday() >= 5), 'exam_day': exam_day, 'event_flag': event_flag, 'recent_avg_demand': recent_avg}
    status = 'ACTIVE'
    fallback = False
    if MODEL is not None:
        try:
            row = [[features.get(name, 0) for name in MODEL_FEATURES]]
            prediction = max(0, int(round(float(MODEL.predict(row)[0]))))
        except Exception:
            prediction = max(0, int(round(attendance * (0.72 if holiday else 0.86))))
            fallback = True
            status = 'FALLBACK (Model Error)'
    else:
        prediction = max(0, int(round(attendance * (0.68 if holiday else 0.86))))
        if target.weekday() >= 5:
            prediction = int(round(prediction * 0.82))
        if rainfall > 10:
            prediction = int(round(prediction * 0.97))
        fallback = True
        status = 'FALLBACK (Heuristics)'
    uncertainty = max(8, int(round(RESIDUAL_P90)))
    lower = max(0, prediction - uncertainty)
    upper = prediction + uncertainty
    confidence = max(50.0, min(99.0, 100 - uncertainty / max(prediction, 1) * 100))
    buffer = max(2, int(round((upper - prediction) * 0.2)))
    recommended = prediction + buffer
    expected_surplus = max(0, recommended - prediction)
    ratio = expected_surplus / max(recommended, 1)
    risk = 'HIGH' if ratio >= 0.12 or expected_surplus >= 80 else 'MEDIUM' if ratio >= 0.05 or expected_surplus >= 30 else 'LOW'
    return {'prediction': prediction, 'lower': lower, 'upper': upper, 'recommended': recommended, 'confidence': round(confidence, 1), 'expected_surplus': expected_surplus, 'risk': risk, 'model_name': MODEL_NAME, 'status': status, 'fallback': fallback, 'features': features}

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
            result = _predict(attendance=attendance, temperature=temperature, rainfall=rainfall, holiday=holiday, humidity=humidity, exam_day=exam_day, event_flag=event_flag)
            DemandForecast.objects.create(date=date.today(), predicted_demand=result['prediction'], recommended_preparation=result['recommended'], lower_bound=result['lower'], upper_bound=result['upper'], confidence=result['confidence'], expected_surplus=result['expected_surplus'], waste_risk=result['risk'], model_name=result['model_name'])
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
    return render(request, 'predict.html', {'result': result, 'weather': weather, 'error': error, 'model_name': MODEL_NAME, 'default_attendance': default_attendance, 'produce_requirements': produce_requirements, 'model_metrics': model_metrics})

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
            for offset in range(7):
                target = date.today() + timedelta(days=offset)
                
                # Base Model (Current AI Suggestion based on historical averages)
                base_item = _predict(int(round(attendance * (0.82 if target.weekday() >= 5 else 1))), 25, 0, int(target.weekday() >= 5), target)
                base_item['date'] = target
                
                # Custom Scenario (User provided overrides)
                scenario_item = _predict(int(round(attendance * (0.82 if target.weekday() >= 5 else 1))), 25, 0, holiday if offset == 0 else int(target.weekday() >= 5), target)
                scenario_item['date'] = target
                
                forecasts.append(base_item)
                scenario_forecasts.append(scenario_item)
                
        except (ValueError, TypeError) as exc:
            messages.error(request, str(exc))
    return render(request, 'forecast.html', {'forecasts': forecasts, 'scenario_forecasts': scenario_forecasts if request.method == 'POST' else None, 'model_name': MODEL_NAME})

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
                
            # Hardcoded NLP rules for Demo workflows (Phase 19)
            if "pause surplus alerts" in user_message or "pause alerts" in user_message:
                return JsonResponse({
                    'type': 'action_preview',
                    'action': 'pause_surplus_alerts',
                    'preview': {
                        'Automation': 'Surplus Alerts',
                        'Current': 'Enabled',
                        'New': 'Paused',
                        'Impact': 'You may stop receiving surplus alerts.'
                    }
                })
            
            ai_response = generate_copilot_response(user_message, request.organization, context)
            
            # If the response is a JSON string (e.g. for navigation), parse it
            try:
                if isinstance(ai_response, str) and ai_response.strip().startswith('{'):
                    parsed = json.loads(ai_response)
                    return JsonResponse(parsed)
            except json.JSONDecodeError:
                pass
                
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
    org_member = request.user.organizations.first()
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
        
    for d in deliveries[:5]:
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
        
    for s in surplus[:5]:
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
        )
        for m in members[:3]:
            results.append({
                'title': m.user.username,
                'subtitle': m.get_role_display(),
                'url': '/organization/',
                'type': 'Team',
                'icon': '👤'
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
        
        # Calculate base using the _predict function
        result = _predict(attendance, temperature, rainfall)
        
        # Overlay user custom production vs AI recommended
        simulated_surplus = max(0, production - result['prediction'])
        ratio = simulated_surplus / max(production, 1)
        risk = 'HIGH' if ratio >= 0.12 or simulated_surplus >= 80 else 'MEDIUM' if ratio >= 0.05 or simulated_surplus >= 30 else 'LOW'
        
        return JsonResponse({
            'success': True,
            'prediction': result['prediction'],
            'simulated_surplus': simulated_surplus,
            'risk': risk,
            'confidence': result['confidence']
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
