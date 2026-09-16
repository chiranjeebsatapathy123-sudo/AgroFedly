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
def volunteer_register(request):
    try:
        profile = request.user.volunteer_profile
    except VolunteerProfile.DoesNotExist:
        profile = None
    if request.method == 'POST':
        form = VolunteerProfileForm(request.POST, instance=profile)
        if form.is_valid():
            volunteer = form.save(commit=False)
            volunteer.user = request.user
            volunteer.save()
            messages.success(request, 'Volunteer profile updated successfully!')
            return redirect('volunteer_dashboard')
    else:
        form = VolunteerProfileForm(instance=profile)
    return render(request, 'volunteer_register.html', {'form': form})

@login_required
def volunteer_dashboard(request):
    try:
        profile = request.user.volunteer_profile
    except VolunteerProfile.DoesNotExist:
        messages.info(request, 'Please register as a volunteer first.')
        return redirect('volunteer_register')
    available_deliveries = Delivery.objects.filter(status='REQUESTED', volunteer_driver__isnull=True).order_by('-created_at')
    my_deliveries = Delivery.objects.filter(volunteer_driver=profile).order_by('-created_at')
    if request.method == 'POST':
        delivery_id = request.POST.get('delivery_id')
        action = request.POST.get('action')
        if delivery_id and action == 'accept':
            delivery = get_object_or_404(Delivery, id=delivery_id)
            if delivery.status == 'REQUESTED' and (not delivery.volunteer_driver):
                delivery.volunteer_driver = profile
                delivery.status = 'ASSIGNED'
                delivery.save()
                messages.success(request, f'You have been assigned to delivery {delivery.tracking_code}.')
                return redirect('volunteer_dashboard')
    return render(request, 'volunteer_dashboard.html', {'profile': profile, 'available_deliveries': available_deliveries, 'my_deliveries': my_deliveries})

@login_required
def user_ai_recipe(request):
    recipe = None
    if request.method == 'POST':
        ingredients = request.POST.get('ingredients', '')
        recipe = {'title': 'Zero-Waste Rustic Veggie Hash', 'ingredients': ingredients.split(','), 'instructions': ['1. Chop all your leftover veggies into small, even cubes.', '2. Sauteé them in olive oil over medium heat until caramelized.', '3. Season with salt, pepper, and paprika.', '4. Serve with a fried egg on top!'], 'waste_saved': '0.5 kg'}
    return render(request, 'user_ai_recipe.html', {'recipe': recipe})



@login_required
def ecosystem_coordination(request):
    try:
        org = request.user.organization
    except:
        return redirect('home')
    alliances = org.alliances.all().select_related('alliance')
    active_alliance = None
    tasks = []
    members = []
    alliance_id = request.GET.get('alliance')
    if alliance_id:
        active_alliance = get_object_or_404(EcosystemAlliance, id=alliance_id)
        if not active_alliance.members.filter(organization=org).exists():
            return redirect('ecosystem_coordination')
        tasks = active_alliance.tasks.all().order_by('-created_at')
        members = active_alliance.members.all().select_related('organization')
    elif alliances.exists():
        active_alliance = alliances.first().alliance
        tasks = active_alliance.tasks.all().order_by('-created_at')
        members = active_alliance.members.all().select_related('organization')
    if request.method == 'POST' and active_alliance:
        action = request.POST.get('action')
        if action == 'create_task':
            title = request.POST.get('title')
            assignee_id = request.POST.get('assignee')
            assignee = None
            if assignee_id:
                assignee = get_object_or_404(Organization, id=assignee_id)
            SharedTask.objects.create(alliance=active_alliance, title=title, created_by=org, assigned_to=assignee)
            return redirect(f"{reverse('ecosystem_coordination')}?alliance={active_alliance.id}")
        elif action == 'update_task_status':
            task_id = request.POST.get('task_id')
            new_status = request.POST.get('status')
            task = get_object_or_404(SharedTask, id=task_id, alliance=active_alliance)
            task.status = new_status
            task.save()
            return redirect(f"{reverse('ecosystem_coordination')}?alliance={active_alliance.id}")
    context = {'org': org, 'alliances': alliances, 'active_alliance': active_alliance, 'tasks': tasks, 'members': members, 'todo_tasks': tasks.filter(status='TODO') if tasks else [], 'inprogress_tasks': tasks.filter(status='IN_PROGRESS') if tasks else [], 'completed_tasks': tasks.filter(status='COMPLETED') if tasks else [], 'total_surplus': SurplusFood.objects.filter(donor=org, status='AVAILABLE').count(), 'total_deliveries': Delivery.objects.filter(logistics_provider=org, status='IN_TRANSIT').count(), 'total_warehouses': Warehouse.objects.filter(owner=org).count()}
    return render(request, 'ecosystem_coordination.html', context)

@login_required
def create_alliance(request):
    try:
        org = request.user.organization
    except:
        return redirect('home')
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        alliance = EcosystemAlliance.objects.create(name=name, description=description)
        AllianceMember.objects.create(alliance=alliance, organization=org, role='Admin')
        return redirect(f"{reverse('ecosystem_coordination')}?alliance={alliance.id}")
    return redirect('ecosystem_coordination')

@login_required
def join_alliance(request):
    try:
        org = request.user.organization
    except:
        return redirect('home')
    if request.method == 'POST':
        alliance_id = request.POST.get('alliance_id')
        alliance = get_object_or_404(EcosystemAlliance, id=alliance_id)
        AllianceMember.objects.get_or_create(alliance=alliance, organization=org)
        return redirect(f"{reverse('ecosystem_coordination')}?alliance={alliance.id}")
    return redirect('ecosystem_coordination')
