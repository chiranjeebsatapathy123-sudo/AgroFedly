from ..decorators import _organization_required, _manager_required, require_role, require_org_role
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

@_organization_required
def organization_dashboard(request):
    org = request.organization
    members = org.members.select_related('user').order_by('-joined_at')
    deliveries = Delivery.objects.filter(Q(sender=org) | Q(receiver=org)).select_related('sender', 'receiver')[:8]
    outgoing = Delivery.objects.filter(sender=org).aggregate(v=Sum('quantity'))['v'] or 0
    incoming = Delivery.objects.filter(receiver=org).aggregate(v=Sum('quantity'))['v'] or 0
    others = OrganizationMember.objects.select_related('organization').filter(user=request.user, is_active=True, organization__is_active=True).exclude(organization=org).order_by('organization__name')
    return render(request, 'organization_dashboard.html', {'organization': org, 'membership': request.membership, 'members': members, 'member_count': members.count(), 'deliveries': deliveries, 'outgoing_quantity': outgoing, 'incoming_quantity': incoming, 'others': others})

def register_organization(request):
    """Register a new organization.

    Anonymous visitors create a new owner account. An already authenticated
    user can register an additional organization and becomes its OWNER; this
    is important for testing and for users who manage multiple institutions.
    """
    if request.method == 'POST':
        form = OrganizationForm(request.POST)
        username = request.POST.get('username', '').strip()
        email = request.POST.get('account_email', '').strip()
        password = request.POST.get('password', '')
        password2 = request.POST.get('password2', '')
        if request.user.is_authenticated:
            if form.is_valid():
                with transaction.atomic():
                    organization = form.save()
                    membership, _ = OrganizationMember.objects.get_or_create(organization=organization, user=request.user, defaults={'role': 'OWNER', 'is_active': True})
                    membership.role = 'OWNER'
                    membership.is_active = True
                    membership.save(update_fields=['role', 'is_active'])
                request.session['active_organization_id'] = organization.id
                messages.success(request, f'{organization.name} is registered and is now your active organization.')
                return redirect('organization_onboarding')
        elif not username or not password:
            form.add_error(None, 'Login username and password are required.')
        elif password != password2:
            form.add_error(None, 'Passwords do not match.')
        elif User.objects.filter(username=username).exists():
            form.add_error(None, 'That username already exists.')
        elif form.is_valid():
            with transaction.atomic():
                user = User.objects.create_user(username=username, email=email, password=password)
                organization = form.save()
                OrganizationMember.objects.create(organization=organization, user=user, role='OWNER', is_active=True)
            login(request, user)
            request.session['active_organization_id'] = organization.id
            messages.success(request, f'{organization.name} is registered. Welcome to Fedly.')
            return redirect('organization_onboarding')
    else:
        form = OrganizationForm()
    return render(request, 'organization_register.html', {'form': form, 'registering_as_authenticated_user': request.user.is_authenticated})

def organization_switch(request, organization_id):
    """Switch the active organization for users who belong to multiple organizations."""
    membership = get_object_or_404(OrganizationMember, organization_id=organization_id, user=request.user, is_active=True, organization__is_active=True)
    request.session['active_organization_id'] = membership.organization_id
    messages.success(request, f'Active organization changed to {membership.organization.name}.')
    return redirect(request.GET.get('next') or 'organization_dashboard')

@login_required
def organization_details_json(request, organization_id):
    """Return safe contact/address information used by the delivery form."""
    organization = get_object_or_404(Organization, id=organization_id, is_active=True)
    return JsonResponse({'id': organization.id, 'name': organization.name, 'type': organization.get_organization_type_display(), 'address': organization.address, 'city': organization.city, 'state': organization.state, 'country': organization.country, 'phone': organization.phone, 'email': organization.email, 'verified': organization.is_verified})

@_organization_required
def organization_edit(request):
    if request.membership.role not in {'OWNER', 'ADMIN'}:
        messages.error(request, 'Only the owner or administrator can edit organization details.')
        return redirect('organization_dashboard')
    if request.method == 'POST':
        form = OrganizationForm(request.POST, instance=request.organization)
        if form.is_valid():
            form.save()
            messages.success(request, 'Organization details updated.')
            return redirect('organization_dashboard')
    else:
        form = OrganizationForm(instance=request.organization)
    return render(request, 'organization_edit.html', {'form': form, 'organization': request.organization})

@_organization_required
def organization_add_member(request):
    if request.membership.role not in {'OWNER', 'ADMIN'}:
        messages.error(request, 'Only the owner or administrator can manage members.')
        return redirect('organization_dashboard')
    form = MemberForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = User.objects.filter(username=form.cleaned_data['username']).first()
        if not user:
            form.add_error('username', 'No user with that username exists.')
        else:
            member, created = OrganizationMember.objects.get_or_create(organization=request.organization, user=user, defaults={'role': form.cleaned_data['role'], 'is_active': True})
            if not created:
                member.role = form.cleaned_data['role']
                member.is_active = True
                member.save(update_fields=['role', 'is_active'])
                messages.success(request, 'Member role updated.')
            else:
                messages.success(request, 'Member added.')
            return redirect('organization_dashboard')
    return render(request, 'organization_member.html', {'form': form})

@_organization_required
def organization_remove_member(request, member_id):
    if request.membership.role not in {'OWNER', 'ADMIN'}:
        messages.error(request, 'Permission denied.')
        return redirect('organization_dashboard')
    member = get_object_or_404(OrganizationMember, id=member_id, organization=request.organization)
    if member.role == 'OWNER':
        messages.error(request, 'The organization owner cannot be removed.')
    else:
        member.delete()
        messages.success(request, 'Member removed.')
    return redirect('organization_dashboard')

@login_required
@_organization_required
def logistics_map(request):
    deliveries = Delivery.objects.filter(sender=request.organization, status__in=['SCHEDULED', 'IN_TRANSIT'])
    delivery_data = []
    for d in deliveries:
        lat = 18.5204
        lng = 73.8567
        delivery_data.append({'id': d.id, 'tracking_code': d.tracking_code, 'status': d.status, 'lat': lat, 'lng': lng})
    return render(request, 'logistics_map.html', {'deliveries_json': json.dumps(delivery_data)})

@login_required
@_organization_required
def impact_dashboard(request):
    impact, _ = OrganizationImpact.objects.get_or_create(organization=request.organization)
    recent_redistributions = Redistribution.objects.filter(surplus__organization=request.organization).order_by('-distributed_at')[:10]
    chart_labels = []
    chart_data = []
    for r in recent_redistributions:
        date_str = r.distributed_at.strftime('%b %d')
        if date_str not in chart_labels:
            chart_labels.append(date_str)
            chart_data.append(r.quantity)
        else:
            idx = chart_labels.index(date_str)
            chart_data[idx] += r.quantity
    chart_labels.reverse()
    chart_data.reverse()
    all_impacts = OrganizationImpact.objects.select_related('organization').order_by('-impact_points')[:10]
    context = {'active_org': request.organization, 'my_impact': impact, 'all_impacts': all_impacts, 'chart_labels': json.dumps(chart_labels), 'chart_data': json.dumps(chart_data)}
    return render(request, 'impact_dashboard.html', context)

def leaderboard(request):
    top_orgs = OrganizationImpact.objects.select_related('organization').order_by('-impact_points')[:10]
    context = {'top_orgs': top_orgs}
    return render(request, 'leaderboard.html', context)

@login_required
@_organization_required
def org_fleet_routing(request):
    from feedly.models import FleetRoute
    import json, random
    routes = FleetRoute.objects.filter(organization=request.organization).order_by('-created_at')
    if not routes.exists():
        FleetRoute.objects.create(organization=request.organization, driver_name='Ramesh Singh', vehicle_plate='MH-12-AB-1234', optimized_path_json=json.dumps([{'lat': 18.5204, 'lng': 73.8567, 'name': 'Pickup 1'}, {'lat': 18.524, 'lng': 73.85, 'name': 'Dropoff 1'}]), total_distance_km=14.5, status='IN_PROGRESS')
        routes = FleetRoute.objects.filter(organization=request.organization).order_by('-created_at')
    return render(request, 'org_fleet_routing.html', {'routes': routes})


@login_required
@_organization_required
def organization_onboarding(request):
    organization = request.organization
    
    if organization.onboarding_completed:
        return redirect('dashboard')
        
    if request.method == 'POST':
        step = int(request.POST.get('step', 1))
        
        if step == 1:
            organization.onboarding_step = 2
        elif step == 2:
            organization.onboarding_step = 3
        elif step == 3:
            organization.onboarding_step = 4
        elif step == 4:
            organization.onboarding_step = 5
        elif step == 5:
            organization.onboarding_completed = True
            organization.save()
            messages.success(request, 'Onboarding complete! Welcome to AgroFedly.')
            return redirect('dashboard')
            
        organization.save()
        
    return render(request, 'onboarding.html', {'organization': organization})

@login_required
@_organization_required
def data_quality_center(request):
    org = request.organization
    
    # 1. Missing Harvest Dates
    missing_harvest = AgriculturalProduce.objects.filter(supplier=org, harvest_date__isnull=True).count()
    
    # 2. Unknown Quality Produce
    unknown_quality = AgriculturalProduce.objects.filter(supplier=org, quality_grade='').count()
    
    # 3. Recipients Missing Capacity
    missing_capacity = Recipient.objects.filter(organization=org, capacity=0).count()
    
    # 4. Old Deliveries still marked IN_TRANSIT
    from django.utils import timezone
    from datetime import timedelta
    stale_deliveries = Delivery.objects.filter(
        sender=org, 
        status='IN_TRANSIT', 
        dispatched_at__lt=timezone.now() - timedelta(days=2)
    ).count()

    context = {
        'issues': [
            {'title': 'Missing Harvest Dates', 'count': missing_harvest, 'severity': 'critical', 'desc': 'Produce records without a harvest date cannot be reliably tracked for spoilage risk.'},
            {'title': 'Unknown Quality Grades', 'count': unknown_quality, 'severity': 'warning', 'desc': 'Produce lacking a quality grade affects distribution priority and ML models.'},
            {'title': 'Recipients Missing Capacity', 'count': missing_capacity, 'severity': 'info', 'desc': 'Recipients with zero capacity configured may not receive optimal surplus matches.'},
            {'title': 'Stale Transit Deliveries', 'count': stale_deliveries, 'severity': 'critical', 'desc': 'Deliveries marked IN_TRANSIT for over 48 hours require manual verification.'}
        ]
    }
    return render(request, 'data_quality.html', context)

@require_role(['OWNER', 'ADMIN'])
def organization_admin_dashboard(request):
    members = request.organization.members.all().select_related('user')
    audit_logs = getattr(request.organization, 'audit_logs', None)
    logs = audit_logs.all()[:10] if audit_logs else []
    return render(request, 'admin/org_admin_dashboard.html', {
        'members': members,
        'audit_logs': logs,
    })

@require_role(['OWNER', 'ADMIN'])
def organization_admin_members(request):
    members = request.organization.members.all().select_related('user')
    invitations = getattr(request.organization, 'invitations', None)
    pending_invites = invitations.filter(status='PENDING') if invitations else []
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'invite':
            email = request.POST.get('email')
            role = request.POST.get('role', 'STAFF')
            
            # Simple mockup of invite creation
            from ..models import OrganizationInvitation
            from django.utils import timezone
            import datetime
            
            OrganizationInvitation.objects.create(
                organization=request.organization,
                email=email,
                role=role,
                status='PENDING',
                expires_at=timezone.now() + datetime.timedelta(days=7),
                invited_by=request.user
            )
            
            # Audit log
            from ..models import TenantAuditLog
            TenantAuditLog.objects.create(
                organization=request.organization,
                actor=request.user,
                action='MEMBER_INVITED',
                entity_name='OrganizationInvitation',
                metadata={'email': email, 'role': role}
            )
            
            messages.success(request, f'Invitation sent to {email}.')
            return redirect('organization_admin_members')
            
    return render(request, 'admin/org_admin_members.html', {
        'members': members,
        'invitations': pending_invites,
    })

@require_role(['OWNER', 'ADMIN'])
def organization_admin_audit(request):
    audit_logs = getattr(request.organization, 'audit_logs', None)
    logs = audit_logs.all().select_related('actor') if audit_logs else []
    return render(request, 'admin/org_admin_audit.html', {
        'audit_logs': logs,
    })

@require_role(['OWNER', 'ADMIN'])
def organization_admin_settings(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        if name:
            request.organization.name = name
            request.organization.save()
            messages.success(request, 'Organization settings updated successfully.')
            return redirect('organization_admin_settings')
            
    return render(request, 'admin/org_admin_settings.html')
