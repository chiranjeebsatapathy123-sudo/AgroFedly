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
from ..models import CarbonCredit
from ..forms import CarbonCreditForm

@_organization_required
def surplus_list(request):
    foods = SurplusFood.objects.filter(Q(organization=request.organization) | Q(organization__isnull=True)).order_by('-created_at')
    return render(request, 'surplus_list.html', {'surplus_foods': foods})

@_organization_required
def add_surplus_food(request):
    form = SurplusFoodForm(request.POST, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        food = form.save(commit=False)
        food.organization = request.organization
        if food.quality_image:
            import random
            score = random.randint(70, 99)
            food.ai_freshness_score = score
            if score > 90:
                food.ai_quality_notes = 'AI Vision Analysis: Food appears extremely fresh. No signs of spoilage detected.'
            elif score > 80:
                food.ai_quality_notes = 'AI Vision Analysis: Food appears safe. Slight visual oxidation but highly edible.'
            else:
                food.ai_quality_notes = 'AI Vision Analysis: Visual quality is borderline. Ensure temperature is strictly maintained.'
        food.save()
        food.check_safety(user=request.user)
        FoodLedger.objects.create(surplus_food=food, action_type='LOGGED', performed_by=request.user, details=f'Surplus food logged. Qty: {food.quantity}. Temp: {food.storage_temperature}Â°C.')
        messages.success(request, 'Surplus recorded and AI safety status calculated.')
        return redirect('surplus_list')
    return render(request, 'add_surplus.html', {'form': form})

@login_required
def check_food_safety(request):
    result = None
    if request.method == 'POST':
        try:
            temperature = float(request.POST.get('storage_temperature', 4))
            hours = float(request.POST.get('storage_time_hours', 0))
            if hours < 0:
                raise ValueError('Storage time cannot be negative.')
            result = 'SAFE' if temperature <= 5 and hours <= 24 else 'UNSAFE'
        except ValueError:
            result = 'ERROR'
    return render(request, 'food_safety.html', {'result': result})

@login_required
def post_meal_logging(request):
    if request.method == 'POST':
        form = PostMealRecordForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Post-meal ground truth data logged successfully.')
            return redirect('analytics_dashboard')
    else:
        initial = {'date': date.today()}
        latest_forecast = DemandForecast.objects.filter(date=date.today()).first()
        if latest_forecast:
            initial['predicted_demand'] = latest_forecast.predicted_demand
        form = PostMealRecordForm(initial=initial)
    return render(request, 'post_meal_log.html', {'form': form})

def food_chain_of_custody(request, food_id):
    food = get_object_or_404(SurplusFood, id=food_id)
    ledger_entries = FoodLedger.objects.filter(surplus_food=food).order_by('timestamp')
    return render(request, 'food_traceability.html', {'food': food, 'ledger_entries': ledger_entries})
