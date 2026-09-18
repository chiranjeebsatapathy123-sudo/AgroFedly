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
def integration_health(request):
    """System Health and Integration Status Dashboard."""
    latest_meal = MealRecord.objects.order_by('-date', '-id').first()
    latest_iot = IoTTemperatureReading.objects.first()
    
    context = {
        'erp_status': 'Operational' if latest_meal and latest_meal.data_source == 'ERP' else 'Degraded (No recent sync)',
        'iot_status': 'Operational' if latest_iot else 'Offline',
        'last_attendance_date': latest_meal.date if latest_meal else None,
        'server_time': timezone.now(),
        'db_status': 'Operational',
        'cache_status': 'Operational',
        'ai_endpoint_status': 'Operational',
    }
    
    # If explicitly requested as json
    if request.headers.get('Accept') == 'application/json' or request.GET.get('format') == 'json':
        return JsonResponse({
            'status': 'ok', 
            'erp_attendance': bool(latest_meal and latest_meal.data_source == 'ERP'), 
            'iot_temperature': bool(latest_iot), 
            'latest_iot_status': latest_iot.status if latest_iot else None, 
            'latest_iot_temperature': latest_iot.temperature if latest_iot else None, 
            'last_attendance_date': str(latest_meal.date) if latest_meal else None, 
            'server_time': timezone.now().isoformat()
        })
        
        
    return render(request, 'integration_health.html', context)

@login_required
def sync_center(request):
    """Offline PWA Sync Center."""
    return render(request, 'sync_center.html')
