from ..decorators import _organization_required, _manager_required, _membership, require_org_role
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

def home(request):
    return render(request, 'home.html')

@login_required
def dashboard(request):
    predictions = DemandForecast.objects.order_by('-date', '-id')
    surplus = SurplusFood.objects.order_by('-created_at').select_related('organization')
    redistributions = Redistribution.objects.order_by('-distributed_at').select_related('surplus', 'recipient')
    
    # Filter with select_related for performance
    recent_deliveries = Delivery.objects.filter(
        Q(sender__members__user=request.user) | Q(receiver__members__user=request.user)
    ).distinct().select_related('sender', 'receiver', 'surplus')[:6]

    context = {
        'total_predictions': predictions.count(), 
        'total_predicted': predictions.aggregate(v=Sum('predicted_demand'))['v'] or 0, 
        'total_surplus': surplus.aggregate(v=Sum('quantity'))['v'] or 0, 
        'safe_food': surplus.filter(status='SAFE').count(), 
        'redistributed': redistributions.aggregate(v=Sum('quantity'))['v'] or 0, 
        'recipients': Recipient.objects.count(), 
        'verified_recipients': Recipient.objects.filter(verified=True).count(), 
        'recent_predictions': predictions[:6], 
        'recent_surplus': surplus[:6], 
        'recent_deliveries': recent_deliveries, 
        'model_name': MODEL_NAME
    }
    confidences = list(predictions.values_list('confidence', flat=True))
    context['avg_confidence'] = round(sum(confidences) / len(confidences), 1) if confidences else 0
    return render(request, 'dashboard.html', context)

@login_required
def intelligence_center(request):
    """Unified operations intelligence workspace.

    All calculations use the application's stored forecasts, surplus, delivery,
    recipient and meal data. External ERP/IoT integrations are intentionally
    represented as safe input endpoints so the app remains usable without paid
    third-party services.
    """
    today = timezone.localdate()
    forecasts = DemandForecast.objects.order_by('-date', '-id')
    surplus_qs = SurplusFood.objects.select_related('organization').order_by('-created_at')
    meal_qs = MealRecord.objects.order_by('-date', '-id')
    verified = Recipient.objects.filter(verified=True, capacity__gt=0)
    latest = forecasts.first()
    recent_meals = list(meal_qs[:30])
    prepared = sum((m.meals_prepared for m in recent_meals))
    consumed = sum((m.meals_consumed for m in recent_meals))
    tracked_waste = max(prepared - consumed, 0)
    surplus_qty = surplus_qs.aggregate(v=Sum('quantity'))['v'] or 0
    latest_iot = IoTTemperatureReading.objects.first()
    redistributed_qty = Delivery.objects.filter(status='DELIVERED').aggregate(v=Sum('quantity'))['v'] or 0
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
                result = _predict(attendance, 25, 0, 0)
                DemandForecast.objects.create(date=today, predicted_demand=result['prediction'], recommended_preparation=result['recommended'], lower_bound=result['lower'], upper_bound=result['upper'], confidence=result['confidence'], expected_surplus=result['expected_surplus'], waste_risk=result['risk'], model_name=result['model_name'])
                messages.success(request, f"Preparation recommendation: {result['recommended']} meals.")
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
    context = {'today': today, 'latest_forecast': latest, 'tracked_prepared': prepared, 'tracked_consumed': consumed, 'tracked_waste': tracked_waste, 'waste_rate': round(waste_rate, 1), 'surplus_qty': surplus_qty, 'redistributed_qty': redistributed_qty, 'cost_savings': round(avoided_cost, 2), 'carbon_savings': round(avoided_carbon, 2), 'waste_risk_score': risk_score, 'emergency_items': emergency_items[:8], 'routes': routes, 'surplus_points': list(surplus_qs.filter(status__in={'PENDING', 'SAFE'})[:20].values('id', 'food_name', 'quantity', 'storage_temperature', 'status')), 'forecast_alerts': list(forecasts.filter(waste_risk__in={'HIGH', 'MEDIUM'})[:8]), 'latest_iot': latest_iot, 'iot_readings': list(IoTTemperatureReading.objects.all()[:8]), 'accuracy_data': accuracy_data}
    return render(request, 'intelligence.html', context)
