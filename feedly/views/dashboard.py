from ..decorators import _organization_required, _manager_required, require_org_role
import json
import os
from datetime import date, timedelta, datetime
from functools import wraps
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.db import transaction, models
from django.db.models import Sum, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from ..forms import DeliveryForm, MemberForm, OrganizationForm, RedistributionForm, SurplusFoodForm
from ..models import DemandForecast, Delivery, MealRecord, Organization, OrganizationMember, Recipient, Redistribution, SurplusFood, IoTTemperatureReading, Ingredient, OrganizationImpact, SystemEvent, Warehouse, UserTask, DataImport
from ..services.surplus import SurplusCalculator
User = get_user_model()
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
import random
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



@login_required
def dashboard(request):
    org_member = request.user.organization_memberships.first()
    if not org_member:
        messages.warning(request, "You need to join an organization to view the full dashboard.")
        return redirect('index')
        
    org = org_member.organization
    
    if hasattr(org, 'onboarding_completed') and not org.onboarding_completed:
        return redirect('organization_onboarding')
    # Filter strictly by organization
    predictions = DemandForecast.objects.order_by('-date', '-id')
    surplus = SurplusFood.objects.filter(organization=org).order_by('-created_at')
    
    # Deliveries where org is sender or receiver
    recent_deliveries = Delivery.objects.filter(
        Q(sender=org) | Q(receiver=org)
    ).distinct().select_related('sender', 'receiver', 'surplus').order_by('-created_at')[:6]

    redistributions = Redistribution.objects.filter(
        surplus__organization=org
    ).order_by('-distributed_at').select_related('surplus', 'recipient')
    
    # Real KPI calculations
    total_predicted = predictions.aggregate(v=Sum('predicted_demand'))['v'] or 0
    
    surplus_calc = SurplusCalculator(org)
    total_surplus = surplus_calc.get_total_surplus_quantity()
    safe_food_count = surplus_calc.get_safe_surplus_quantity()
    
    total_redistributed = redistributions.aggregate(v=Sum('quantity'))['v'] or 0

    # Priority Center Logic using AI Orchestrator
    from ..ai.orchestrator import AIOrchestrator
    orchestrator = AIOrchestrator(org)
    
    briefing = orchestrator.generate_daily_briefing()
    priorities = orchestrator.get_attention_items()
    
    # We still need top priorities for dashboard summary cards
    dashboard_priorities = priorities[:4] if priorities else []

    # Map orchestrator output to template expectations
    mapped_priorities = []
    icon_map = {"CRITICAL": "🔴", "URGENT": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🔵"}
    for p in dashboard_priorities:
        mapped_priorities.append({
            'type': p['severity'].lower(),
            'icon': icon_map.get(p['severity'], '🔵'),
            'title': p['title'],
            'desc': p['description'],
            'action_url': p['action_url'],
            'action_text': p['action_text']
        })

    # Generate Daily Briefing Text
    briefing_text = "No major operational issues detected from the available data."
    if briefing['signals']:
        briefing_text = "Today's operations show " + ", ".join([s['message'].lower().replace('.', '') for s in briefing['signals'][:3]]) + "."

    # Calculate additional metrics for redesign
    production_total = AgriculturalProduce.objects.filter(organization=org).aggregate(v=Sum('quantity_kg'))['v'] or 0
    available_produce = AgriculturalProduce.objects.filter(organization=org, status='HARVESTED').aggregate(v=Sum('quantity_kg'))['v'] or 0

    context = {
        'production_total': round(production_total, 1),
        'demand_forecast_total': round(total_predicted, 1),
        'available_produce': round(available_produce, 1),
        'total_predictions': predictions.count(), 
        'total_predicted': total_predicted, 
        'total_surplus': round(total_surplus, 1), 
        'safe_food': safe_food_count, 
        'redistributed': round(total_redistributed, 1),
        'impact': f"{round(total_redistributed * 2.5 / 1000, 1)}k", # 2.5 meals per kg
        'recipients': Recipient.objects.filter(organization=org).count(), 
        'verified_recipients': Recipient.objects.filter(organization=org, verified=True).count(), 
        'recent_predictions': predictions[:6], 
        'recent_surplus': surplus[:6], 
        'recent_deliveries': recent_deliveries, 
        'priorities': mapped_priorities,
        'model_name': "AgroFedly AI 1.0",
        'organization': org,
        'daily_briefing_text': briefing_text,
        'briefing_counts': {
            'priorities': len(priorities),
            'deliveries': Delivery.objects.filter(sender=org, status__in=['PENDING', 'IN_TRANSIT']).count(),
            'storage_alerts': IoTTemperatureReading.objects.filter(status='ALERT', recorded_at__date=timezone.now().date()).count(), 
            'ai_recommendations': briefing['attention_count']
        }
    }
    confidences = list(predictions.values_list('confidence', flat=True))
    from ..models import UserTask
    tasks = UserTask.objects.filter(organization=org, assigned_to=request.user, status__in=['OPEN', 'IN_PROGRESS']).order_by('-priority', 'due_date')[:5]
    if not tasks.exists():
        tasks = UserTask.objects.filter(organization=org, assigned_to=None, status__in=['OPEN', 'IN_PROGRESS']).order_by('-priority', 'due_date')[:5]
    context['my_tasks'] = tasks
    
    return render(request, 'dashboard.html', context)
@login_required
def digital_twin(request):
    """Real-Time Digital Twin representation of the ecosystem."""
    org = request.user.organization
    
    # 1. Fetch system state
    events = SystemEvent.objects.filter(organization=org).order_by('-timestamp')[:10]
    
    # 2. Risk Radar calculation (simulated for demo based on rules)
    # Demand Risk, Surplus Risk, Storage Risk
    surplus_count = SurplusFood.objects.filter(organization=org, is_active=True).count()
    surplus_risk = 3 if surplus_count > 10 else (2 if surplus_count > 5 else 1)
    
    # Storage Risk
    storage_capacity = sum([w.capacity_kg for w in Warehouse.objects.filter(organization=org)]) or 1
    storage_used = sum([w.current_load_kg for w in Warehouse.objects.filter(organization=org)]) or 0
    storage_util = storage_used / storage_capacity
    storage_risk = 3 if storage_util > 0.9 else (2 if storage_util > 0.7 else 1)
    
    context = {
        'events': events,
        'surplus_risk': surplus_risk,
        'storage_risk': storage_risk,
        'is_digital_twin': True,
    }
    return render(request, 'digital_twin.html', context)

@login_required
def produce_passport(request, batch_id):
    """Visual Digital Passport timeline for a batch."""
    org = request.user.organization
    
    # We construct a timeline based on the batch ID
    # In a real app we'd query AgriculturalProduce, ProcessingRecord, StorageRecord etc.
    timeline = [
        {'time': '2026-09-14 08:00', 'title': 'Harvest Recorded', 'desc': 'Batch logged at Farm 1', 'status': 'success'},
        {'time': '2026-09-14 12:00', 'title': 'Quality Inspection', 'desc': 'Passed internal check', 'status': 'success'},
        {'time': '2026-09-15 09:30', 'title': 'Storage Entry', 'desc': 'Logged into Cold Storage B', 'status': 'success'},
        {'time': '2026-09-16 10:00', 'title': 'Surplus Detected', 'desc': 'AI flagged excess batch', 'status': 'warning'},
        {'time': '2026-09-16 14:00', 'title': 'Redistribution Matched', 'desc': 'Allocated to Shelter A', 'status': 'info'},
    ]
    
    context = {
        'batch_id': batch_id,
        'timeline': timeline,
    }
    return render(request, 'produce_passport.html', context)

@login_required
def data_import(request):
    """Data Import Center for CSVs."""
    org = request.user.organization
    imports = DataImport.objects.filter(organization=org).order_by('-created_at')
    
    context = {
        'imports': imports
    }
    return render(request, 'data_import.html', context)

@login_required
def intelligence_center(request):
    """Unified operations intelligence workspace."""
    org_member = request.user.organization_memberships.first()
    if not org_member:
        messages.warning(request, "You need to join an organization to view intelligence.")
        return redirect('home')
        
    org = org_member.organization
    today = timezone.localdate()
    
    forecasts = DemandForecast.objects.order_by('-date', '-id')
    surplus_qs = SurplusFood.objects.filter(organization=org).select_related('organization').order_by('-created_at')
    
    # Actually filter MealRecord by organization if it were linked, but MealRecord currently is global per project
    # We will assume MealRecord belongs to the current org context for this demo
    meal_qs = MealRecord.objects.order_by('-date', '-id')
    verified = Recipient.objects.filter(organization=org, verified=True, capacity__gt=0)
    
    latest = forecasts.first()
    recent_meals = list(meal_qs[:30])
    prepared = sum((m.meals_prepared for m in recent_meals))
    consumed = sum((m.meals_consumed for m in recent_meals))
    tracked_waste = max(prepared - consumed, 0)
    
    surplus_calc = SurplusCalculator(org)
    surplus_qty = surplus_calc.get_total_surplus_quantity()
    
    latest_iot = IoTTemperatureReading.objects.filter(organization=org).order_by('-recorded_at').first()
    
    redistributed_qty = Delivery.objects.filter(sender=org, status='DELIVERED').aggregate(v=Sum('quantity'))['v'] or 0
    meal_cost = 35.0
    carbon_per_meal_kg = 0.65
    avoided_cost = redistributed_qty * meal_cost
    avoided_carbon = redistributed_qty * carbon_per_meal_kg
    waste_rate = tracked_waste / prepared * 100 if prepared else 0
    forecast_surplus = latest.expected_surplus if latest else 0
    risk_score = min(100, round(waste_rate * 1.5 + (forecast_surplus / max(latest.recommended_preparation, 1) * 55 if latest else 0) + (surplus_qty / max(prepared, 1) * 20 if prepared else 0)))
    
    emergency_items = []
    now = timezone.now()
    for item in surplus_qs.filter(status__in={'PENDING', 'SAFE'}):
        age = (now - item.created_at).total_seconds() / 3600
        if item.storage_temperature > 5 or item.storage_time_hours > 24 or age >= 18 or (item.quantity >= 100):
            emergency_items.append({'food': item.food_name, 'quantity': item.quantity, 'age_hours': round(max(age, item.storage_time_hours), 1), 'reason': 'Temperature/time threshold' if item.storage_temperature > 5 or item.storage_time_hours > 24 else 'Rapid redistribution required'})
            
    routes = []
    for recipient in verified.order_by('distance_km', '-urgency_score')[:10]:
        score = min(recipient.capacity, max(surplus_qty, 1)) / max(max(surplus_qty, 1), 1) * 0.45 + 1 / (1 + max(recipient.distance_km, 0)) * 0.3 + recipient.urgency_score / 100 * 0.25
        routes.append({'name': recipient.name, 'distance': round(recipient.distance_km, 1), 'urgency': recipient.urgency_score, 'capacity': recipient.capacity, 'score': round(score * 100, 1)})
    if request.method == 'POST':
        action = request.POST.get('action', '').strip()
        try:
            if action == 'track_consumption':
                record_date = request.POST.get('date') or str(today)
                record_date = datetime.strptime(record_date, '%Y-%m-%d').date()
                attendance = int(request.POST.get('attendance', 0))
                prepared_count = int(request.POST.get('prepared', 0))
                consumed_count = int(request.POST.get('consumed', 0))
                if min(attendance, prepared_count, consumed_count) < 0:
                    raise ValueError('Consumption values cannot be negative.')
                if consumed_count > prepared_count:
                    raise ValueError('Consumed meals cannot exceed prepared meals.')
                MealRecord.objects.create(date=record_date, attendance=attendance, meals_prepared=prepared_count, meals_consumed=consumed_count, location=request.POST.get('location', 'Project Site')[:120], data_source='MANUAL')
                messages.success(request, 'Consumption data recorded.')
            elif action == 'erp_attendance':
                attendance = int(request.POST.get('attendance', 0))
                if attendance < 0:
                    raise ValueError('Attendance cannot be negative.')
                MealRecord.objects.create(date=today, attendance=attendance, meals_prepared=0, meals_consumed=0, data_source='ERP')
                messages.success(request, 'ERP attendance sync recorded successfully.')
            elif action == 'iot_temperature':
                temperature = float(request.POST.get('temperature', 0))
                food_name = request.POST.get('food_name', 'IoT monitored food')[:100]
                sensor_name = request.POST.get('sensor_name', 'Manual / IoT Sensor')[:100]
                location = request.POST.get('sensor_location', '')[:150]
                safe = -1 <= temperature <= 5
                reading = IoTTemperatureReading.objects.create(sensor_name=sensor_name, food_name=food_name, temperature=temperature, location=location, status='SAFE' if safe else 'ALERT')
                messages.success(request, f"IoT reading #{reading.id} stored: {temperature:.1f}Â°C â€” {('SAFE' if safe else 'CHECK STORAGE')} for {food_name}.")
            elif action == 'preparation':
                attendance = int(request.POST.get('attendance', 0))
                if attendance < 0:
                    raise ValueError('Attendance cannot be negative.')
                from ..services.forecasting import DemandForecastingPipeline
                pipeline = DemandForecastingPipeline(org)
                result = pipeline.predict_demand(attendance, target_date=today)
                messages.success(request, f"Preparation recommendation: {result.recommended_preparation} meals.")
            elif action in ['accept_recommendation', 'reject_recommendation', 'dismiss_recommendation']:
                from feedly.models import AIRecommendation
                rec_id = request.POST.get('recommendation_id')
                if rec_id:
                    rec = get_object_or_404(AIRecommendation, id=rec_id, organization=org)
                    if action == 'accept_recommendation':
                        rec.status = 'ACCEPTED'
                        messages.success(request, f'Recommendation accepted: {rec.title}')
                    elif action == 'reject_recommendation':
                        rec.status = 'REJECTED'
                        rec.feedback_notes = request.POST.get('feedback', '')
                        messages.warning(request, 'Recommendation rejected. Feedback logged.')
                    elif action == 'dismiss_recommendation':
                        rec.status = 'VIEWED'
                        messages.info(request, 'Recommendation dismissed.')
                    rec.save(update_fields=['status', 'feedback_notes'])
            else:
                messages.info(request, 'Action is ready for the next operation.')
        except (ValueError, TypeError) as exc:
            messages.error(request, str(exc))
        return redirect('intelligence_center')
    recent_forecasts = list(forecasts[:7])
    recent_meals_dict = {m.date: m.meals_consumed for m in MealRecord.objects.filter(date__in=[f.date for f in recent_forecasts]).exclude(data_source='ERP')}
    accuracy_data = []
    for f in recent_forecasts:
        actual = recent_meals_dict.get(f.date)
        if actual is not None and actual > 0:
            diff = abs(f.predicted_demand - actual)
            accuracy = max(0, 100 - diff / max(actual, 1) * 100)
            accuracy_data.append({'date': f.date.strftime('%b %d'), 'predicted': f.predicted_demand, 'actual': actual, 'accuracy': round(accuracy, 1)})
            
    from feedly.models import AIRecommendation
    ai_recommendations = AIRecommendation.objects.filter(organization=org, status='NEW').order_by(
        models.Case(
            models.When(priority='URGENT', then=0),
            models.When(priority='HIGH', then=1),
            models.When(priority='MEDIUM', then=2),
            models.When(priority='LOW', then=3),
            default=4,
        ),
        '-created_at'
    )
    
    # System Status Mock Check (derived from our health_check logic in api.py)
    system_status = {
        'database': 'Operational',
        'redis': 'Operational' if hasattr(settings, 'CHANNEL_LAYERS') else 'Degraded (In-Memory)',
        'ml_model': 'Operational' if MODEL else 'Degraded (Fallback active)'
    }
            
    context = {'today': today, 'latest_forecast': latest, 'tracked_prepared': prepared, 'tracked_consumed': consumed, 'tracked_waste': tracked_waste, 'waste_rate': round(waste_rate, 1), 'surplus_qty': surplus_qty, 'redistributed_qty': redistributed_qty, 'cost_savings': round(avoided_cost, 2), 'carbon_savings': round(avoided_carbon, 2), 'waste_risk_score': risk_score, 'emergency_items': emergency_items[:8], 'routes': routes, 'surplus_points': list(surplus_qs.filter(status__in={'PENDING', 'SAFE'})[:20].values('id', 'food_name', 'quantity', 'storage_temperature', 'status')), 'forecast_alerts': list(forecasts.filter(waste_risk__in={'HIGH', 'MEDIUM'})[:8]), 'latest_iot': latest_iot, 'iot_readings': list(IoTTemperatureReading.objects.filter(organization=request.organization)[:8]), 'accuracy_data': accuracy_data, 'ai_recommendations': ai_recommendations, 'system_status': system_status}
    return render(request, 'intelligence.html', context)
