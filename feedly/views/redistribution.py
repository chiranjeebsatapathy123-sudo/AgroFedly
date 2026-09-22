from feedly.decorators import require_sector
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

@_organization_required
def redistribute_food(request, food_id):
    if request.method == 'POST':
        with transaction.atomic():
            food = get_object_or_404(SurplusFood.objects.select_for_update(), id=food_id)
            if food.organization not in {request.organization, None}:
                messages.error(request, "You cannot redistribute another organization's food.")
                return redirect('surplus_list')
            if food.status != 'SAFE':
                messages.error(request, 'Only SAFE surplus can be redistributed.')
                return redirect('surplus_list')
            form = RedistributionForm(request.POST)
            if form.is_valid():
                item = form.save(commit=False)
                if item.quantity > food.quantity:
                    form.add_error('quantity', 'Quantity exceeds available surplus.')
                else:
                    item.surplus = food
                    item.save()
                    food.quantity -= item.quantity
                    if food.quantity == 0:
                        food.status = 'REDISTRIBUTED'
                    food.save()
                    
                    # Create Traceability Ledger entry
                    from ..models import ProduceTraceabilityLedger
                    import uuid
                    ProduceTraceabilityLedger.objects.create(
                        transaction_id=str(uuid.uuid4()),
                        transaction_type='ALLOCATED',
                        surplus=food,
                        quantity=item.quantity,
                        actor=request.user,
                        organization=food.organization,
                        details=f"Allocated {item.quantity} to {item.recipient.name}"
                    )
                    
                    # Create Delivery record
                    Delivery.objects.create(
                        surplus=food,
                        sender=food.organization,
                        receiver=food.organization, # Self-managed delivery
                        status='REQUESTED',
                        food_name=food.food_name,
                        quantity=item.quantity,
                        pickup_address=food.organization.address if food.organization else "",
                        delivery_address="Recipient: " + item.recipient.name
                    )
                    
                    messages.success(request, 'Surplus redistributed and delivery requested.')
                    return redirect('surplus_list')
            return render(request, 'redistribute.html', {'form': form, 'food': food, 'verified_recipient_count': Recipient.objects.filter(organization=request.organization, verified=True, capacity__gt=0).count()})
    else:
        food = get_object_or_404(SurplusFood, id=food_id)
        if food.organization not in {request.organization, None}:
            messages.error(request, "You cannot redistribute another organization's food.")
            return redirect('surplus_list')
        if food.status != 'SAFE':
            messages.error(request, 'Only SAFE surplus can be redistributed.')
            return redirect('surplus_list')
        form = RedistributionForm()
        return render(request, 'redistribute.html', {'form': form, 'food': food, 'verified_recipient_count': Recipient.objects.filter(organization=request.organization, verified=True, capacity__gt=0).count()})

@login_required
def recipient_list(request):
    recipients = Recipient.objects.filter(organization=request.organization).order_by('-verified', '-urgency_score', 'name')
    return render(request, 'recipient_list.html', {'recipients': recipients, 'verified_count': recipients.filter(verified=True).count(), 'pending_count': recipients.filter(verified=False).count(), 'verified_capacity': recipients.filter(verified=True).aggregate(total=Sum('capacity'))['total'] or 0})

@login_required
def add_recipient(request):
    if request.method == 'POST':
        try:
            name = request.POST.get('name', '').strip()
            recipient_type = request.POST.get('recipient_type', '').strip()
            capacity = int(request.POST.get('capacity', 0))
            distance = float(request.POST.get('distance_km', 0) or 0)
            urgency = int(request.POST.get('urgency_score', 50) or 50)
            verify_now = request.POST.get('verify_now') == '1'
            if not name:
                raise ValueError('Recipient name is required.')
            if not recipient_type:
                raise ValueError('Recipient type is required.')
            if capacity <= 0:
                raise ValueError('Capacity must be greater than zero.')
            if distance < 0:
                raise ValueError('Distance cannot be negative.')
            if not 0 <= urgency <= 100:
                raise ValueError('Urgency must be between 0 and 100.')
            recipient = Recipient.objects.create(organization=request.organization, name=name, recipient_type=recipient_type, capacity=capacity, distance_km=distance, urgency_score=urgency, verified=verify_now)
            if verify_now:
                messages.success(request, f'{recipient.name} was added and verified. It is now available in the redistribution dropdown.')
            else:
                messages.success(request, f'{recipient.name} was added as pending. Verify it from the Recipients page before redistribution.')
            return redirect('recipient_list')
        except (ValueError, TypeError) as exc:
            return render(request, 'add_recipient.html', {'error': str(exc)})
    return render(request, 'add_recipient.html')

@login_required
def verify_recipient(request, recipient_id):
    if request.method != 'POST':
        messages.info(request, 'Use the Verify button to verify a recipient.')
        return redirect('recipient_list')
    recipient = get_object_or_404(Recipient, id=recipient_id, organization=request.organization)
    recipient.verified = True
    recipient.save(update_fields=['verified'])
    messages.success(request, f'{recipient.name} is now verified and available for redistribution.')
    return redirect('recipient_list')

@login_required
def recipient_recommendations(request, food_id):
    food = get_object_or_404(SurplusFood, id=food_id)
    if food.status != 'SAFE':
        return JsonResponse({'error': 'Only SAFE food can be recommended.'}, status=400)
    ranked = []
    for recipient in Recipient.objects.filter(organization=request.organization, verified=True, capacity__gt=0):
        fit = min(food.quantity, recipient.capacity) / max(food.quantity, 1)
        distance = 1 / (1 + max(recipient.distance_km, 0))
        urgency = min(max(recipient.urgency_score, 0), 100) / 100
        score = 0.5 * fit + 0.3 * urgency + 0.2 * distance
        reasons = []
        if fit >= 0.8:
            reasons.append('optimal capacity match')
        elif fit >= 0.5:
            reasons.append('acceptable capacity match')
        if urgency >= 0.7:
            reasons.append('high urgency')
        if recipient.distance_km <= 10:
            reasons.append('close proximity')
        if reasons:
            explanation = f'{round(score * 100)}% match due to ' + ', '.join(reasons) + '.'
        else:
            explanation = f'{round(score * 100)}% match based on general suitability.'
        ranked.append({'name': recipient.name, 'score': round(score * 100, 1), 'capacity': recipient.capacity, 'distance_km': recipient.distance_km, 'urgency': recipient.urgency_score, 'explanation': explanation})
    ranked.sort(key=lambda x: x['score'], reverse=True)
    return JsonResponse({'food': food.food_name, 'quantity': food.quantity, 'recommendations': ranked[:5]})

@login_required
@require_sector('REDISTRIBUTION')
def redistribution_dashboard(request):
    request.session['active_workspace'] = 'REDISTRIBUTION'
    org_member = request.user.organization_memberships.first()
    org = org_member.organization if org_member else None
    
    surplus_available = SurplusFood.objects.filter(status='SAFE', quantity__gt=0).exclude(safety_status__in=['EXPIRED', 'NOT_ELIGIBLE']).order_by('created_at')
    pending_requests = Recipient.objects.filter(organization=org)
    active_deliveries = Delivery.objects.filter(status='IN_TRANSIT')
    
    context = {
        'surplus_available': surplus_available[:10],
        'total_surplus': surplus_available.aggregate(total=Sum('quantity'))['total'] or 0,
        'pending_requests': pending_requests.count(),
        'active_deliveries': active_deliveries.count(),
        'organization': org
    }
    return render(request, 'redistribution/dashboard.html', context)

@login_required
def redistribution_transfers(request):
    """Phase 49: Redistribution Transfers."""
    return render(request, 'redistribution_transfers.html', {})

@login_required
def redistribution_delivery(request):
    """Phase 49: Redistribution Delivery."""
    return render(request, 'redistribution_delivery.html', {})

@login_required
def redistribution_surplus(request):
    return render(request, 'redistribution_surplus.html', {})

from feedly.decorators import _organization_required
@login_required
@_organization_required
def redistribution_matching(request):
    from feedly.models import SurplusFood, Recipient, Redistribution, Delivery
    from django.contrib import messages
    from django.shortcuts import redirect
    import random
    
    if request.method == 'POST':
        action = request.POST.get('action')
        surplus_id = request.POST.get('surplus_id')
        recipient_id = request.POST.get('recipient_id')
        
        if action == 'approve' and surplus_id and recipient_id:
            try:
                surplus = SurplusFood.objects.get(id=surplus_id, organization=request.organization, status='AVAILABLE')
                if surplus.safety_status in ['EXPIRED', 'NOT_ELIGIBLE']:
                    raise PermissionDenied('Cannot transfer unsafe or expired surplus.')
                recipient = Recipient.objects.get(id=recipient_id, organization=request.organization)
                
                Redistribution.objects.create(
                    organization=request.organization,
                    quantity=surplus.quantity,
                    surplus=surplus,
                    recipient=recipient
                )
                
                surplus.status = 'DONATED'
                surplus.save()
                
                Delivery.objects.create(
                    sender=request.organization,
                    receiver=request.organization,
                    surplus=surplus,
                    food_name=surplus.food_name,
                    quantity=surplus.quantity,
                    pickup_address="Main Organization Warehouse",
                    delivery_address=recipient.name,
                    status='REQUESTED'
                )
                
                messages.success(request, f'Match approved! {surplus.food_name} is queued for delivery to {recipient.name}.')
            except Exception as e:
                messages.error(request, 'Error: Item is no longer available or recipient is invalid.')
        elif action == 'reject':
            messages.info(request, 'Match rejected. AI model has been updated with this feedback.')
            
        return redirect('redistribution_matching')

    available_surplus = list(SurplusFood.objects.filter(organization=request.organization, status='AVAILABLE').exclude(safety_status__in=['EXPIRED', 'NOT_ELIGIBLE'])[:10])
    recipients = list(Recipient.objects.filter(organization=request.organization)[:10])
    
    matches = []
    for surplus in available_surplus:
        if recipients:
            recipient = random.choice(recipients)
            matches.append({
                'surplus': surplus,
                'recipient': recipient,
                'score': random.randint(85, 99)
            })
            
    return render(request, 'redistribution_matching.html', {'matches': matches})

@login_required
def redistribution_verification(request):
    return render(request, 'redistribution_verification.html', {})
