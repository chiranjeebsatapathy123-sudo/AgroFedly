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

from django.db import connection
def health_check(request):
    try:
        connection.ensure_connection()
        return JsonResponse({'status': 'ok', 'service': 'Fedly', 'database': 'connected'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'service': 'Fedly', 'database': 'disconnected', 'error': str(e)}, status=503)

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
    return {'prediction': prediction, 'lower': lower, 'upper': upper, 'recommended': recommended, 'confidence': round(confidence, 1), 'expected_surplus': expected_surplus, 'risk': risk, 'model_name': MODEL_NAME, 'status': status, 'fallback': fallback}

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
    produce_requirements = []
    if result:
        ingredients = Ingredient.objects.filter(is_active=True)
        for ingredient in ingredients:
            produce_requirements.append({'name': ingredient.name, 'unit': ingredient.unit, 'required': round(result['prediction'] * ingredient.quantity_per_meal, 2), 'recommended': round(result['recommended'] * ingredient.quantity_per_meal, 2), 'buffer': round((result['recommended'] - result['prediction']) * ingredient.quantity_per_meal, 2)})
    return render(request, 'predict.html', {'result': result, 'weather': weather, 'error': error, 'model_name': MODEL_NAME, 'default_attendance': default_attendance, 'produce_requirements': produce_requirements})

@login_required
def forecast_7_days(request):
    forecasts = []
    if request.method == 'POST':
        try:
            attendance = int(request.POST.get('attendance', 0))
            holiday = int(request.POST.get('holiday', 0))
            if attendance <= 0:
                raise ValueError('Attendance must be greater than zero.')
            for offset in range(7):
                target = date.today() + timedelta(days=offset)
                item = _predict(int(round(attendance * (0.82 if target.weekday() >= 5 else 1))), 25, 0, holiday if offset == 0 else int(target.weekday() >= 5), target)
                item['date'] = target
                item['produce_requirements'] = []
                ingredients = Ingredient.objects.filter(is_active=True)
                for ingredient in ingredients:
                    item['produce_requirements'].append({'name': ingredient.name, 'unit': ingredient.unit, 'required': round(item['prediction'] * ingredient.quantity_per_meal, 2), 'recommended': round(item['recommended'] * ingredient.quantity_per_meal, 2), 'buffer': round((item['recommended'] - item['prediction']) * ingredient.quantity_per_meal, 2)})
                forecasts.append(item)
        except (ValueError, TypeError) as exc:
            messages.error(request, str(exc))
    return render(request, 'forecast.html', {'forecasts': forecasts, 'model_name': MODEL_NAME})

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

@csrf_exempt
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

@csrf_exempt
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
        fluctuation = random.uniform(-0.5, 0.5)
        new_temp = round(current + fluctuation, 1)
        shipment.current_temperature = new_temp
        shipment.save(update_fields=['current_temperature'])
        data.append({'tracking_code': shipment.tracking_code, 'temperature': new_temp, 'status': 'Warning' if new_temp > 6.0 or new_temp < 0.0 else 'Normal'})
    return JsonResponse({'status': 'success', 'data': data})

@csrf_exempt
@_organization_required
def copilot_chat(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_message = data.get('message', '')
            if not user_message:
                return JsonResponse({'error': 'No message provided'}, status=400)
            ai_response = generate_copilot_response(user_message, request.organization)
            return JsonResponse({'response': ai_response})
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
    return JsonResponse({'error': 'Method not allowed'}, status=405)
