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

@login_required
def analytics_dashboard(request):
    meal_records = MealRecord.objects.filter(discarded_meals__gt=0).order_by('-date') | MealRecord.objects.filter(meals_prepared__gt=0, meals_consumed__gt=0).order_by('-date')
    total_prepared_meals = meal_records.aggregate(v=Sum('meals_prepared'))['v'] or 0
    total_consumed_meals = meal_records.aggregate(v=Sum('meals_consumed'))['v'] or 0
    total_discarded_meals = meal_records.aggregate(v=Sum('discarded_meals'))['v'] or 0
    utilization_rate = total_consumed_meals / total_prepared_meals * 100 if total_prepared_meals > 0 else 0
    ingredients = Ingredient.objects.filter(is_active=True)
    total_produce_waste_kg = 0
    monetary_value_waste = 0
    top_wasted = []
    for ing in ingredients:
        wasted_qty = total_discarded_meals * ing.quantity_per_meal
        waste_value = wasted_qty * ing.cost_per_unit
        total_produce_waste_kg += wasted_qty
        monetary_value_waste += waste_value
        top_wasted.append({'name': ing.name, 'wasted_qty': round(wasted_qty, 2), 'unit': ing.unit, 'waste_value': round(waste_value, 2)})
    top_wasted = sorted(top_wasted, key=lambda x: x['waste_value'], reverse=True)[:5]
    baseline_waste_meals = total_prepared_meals * 0.2
    saved_meals = max(0, baseline_waste_meals - total_discarded_meals)
    savings_value = sum([saved_meals * ing.quantity_per_meal * ing.cost_per_unit for ing in ingredients])
    chart_records = meal_records.exclude(predicted_demand=0).exclude(predicted_demand__isnull=True).order_by('-date')[:7]
    chart_records = list(reversed(chart_records))
    context = {'utilization_rate': round(utilization_rate, 1), 'total_produce_waste': round(total_produce_waste_kg, 2), 'monetary_value_waste': round(monetary_value_waste, 2), 'savings_value': round(savings_value, 2), 'top_wasted': top_wasted, 'chart_records': chart_records}
    return render(request, 'analytics.html', context)
