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
def delivery_list(request):
    deliveries = Delivery.objects.filter(Q(sender=request.organization) | Q(receiver=request.organization)).select_related('sender', 'receiver', 'surplus')
    search = request.GET.get('q', '').strip()
    status = request.GET.get('status', '').strip().upper()
    if search:
        deliveries = deliveries.filter(Q(tracking_code__icontains=search) | Q(food_name__icontains=search) | Q(driver_name__icontains=search) | Q(vehicle_number__icontains=search) | Q(receiver__name__icontains=search) | Q(sender__name__icontains=search))
    valid_statuses = {value for value, _ in Delivery.STATUS_CHOICES}
    if status in valid_statuses:
        deliveries = deliveries.filter(status=status)
    else:
        status = ''
    all_deliveries = Delivery.objects.filter(Q(sender=request.organization) | Q(receiver=request.organization))
    status_counts = {value: all_deliveries.filter(status=value).count() for value, _ in Delivery.STATUS_CHOICES}
    return render(request, 'delivery_list.html', {'deliveries': deliveries, 'organization': request.organization, 'search': search, 'active_status': status, 'status_counts': status_counts, 'total_deliveries': all_deliveries.count(), 'active_deliveries': all_deliveries.exclude(status__in={'DELIVERED', 'CANCELLED'}).count(), 'delivered_deliveries': all_deliveries.filter(status='DELIVERED').count()})

@_organization_required
def delivery_create(request):
    form = DeliveryForm(request.POST or None, sender=request.organization)
    receiver_count = form.fields['receiver'].queryset.count()
    if request.method == 'POST' and receiver_count == 0:
        form.add_error(None, 'Register another active organization before creating a delivery.')
    elif request.method == 'POST' and form.is_valid():
        delivery = form.save(commit=False)
        delivery.sender = request.organization
        delivery.created_by = request.user
        delivery.status = 'ASSIGNED' if delivery.driver_name else 'REQUESTED'
        if not delivery.pickup_address:
            delivery.pickup_address = request.organization.address
        with transaction.atomic():
            if delivery.surplus_id:
                surplus = SurplusFood.objects.select_for_update().get(id=delivery.surplus_id)
                if delivery.quantity > surplus.quantity:
                    form.add_error('quantity', 'Delivery quantity exceeds linked surplus.')
                    return render(request, 'delivery_form.html', {'form': form, 'organization': request.organization, 'receiver_count': receiver_count})
                
                delivery.save()
                surplus.quantity -= delivery.quantity
                if surplus.quantity == 0:
                    surplus.status = 'REDISTRIBUTED'
                surplus.save(update_fields=['quantity', 'status'])
            else:
                delivery.save()
                
            messages.success(request, f'Delivery created. Tracking: {delivery.tracking_code}')
            return redirect('delivery_detail', delivery_id=delivery.id)
    return render(request, 'delivery_form.html', {'form': form, 'organization': request.organization, 'receiver_count': receiver_count})

@_organization_required
def delivery_detail(request, delivery_id):
    delivery = get_object_or_404(Delivery.objects.select_related('sender', 'receiver', 'surplus', 'created_by'), id=delivery_id)
    if delivery.sender_id != request.organization.id and delivery.receiver_id != request.organization.id:
        messages.error(request, 'You do not have access to this delivery.')
        return redirect('delivery_list')
    from .utils import geocode_address, get_osrm_route
    route_data = None
    start_lat, start_lng = geocode_address(f'{delivery.pickup_address}, {delivery.sender.city}')
    end_lat, end_lng = geocode_address(f'{delivery.delivery_address}, {delivery.receiver.city}')
    if start_lat and end_lat:
        route_data = get_osrm_route(start_lat, start_lng, end_lat, end_lng)
    return render(request, 'delivery_detail.html', {'delivery': delivery, 'organization': request.organization, 'route_data': route_data, 'start_coords': {'lat': start_lat, 'lng': start_lng} if start_lat else None, 'end_coords': {'lat': end_lat, 'lng': end_lng} if end_lat else None})

@_organization_required
def delivery_update_status(request, delivery_id):
    delivery = get_object_or_404(Delivery.objects.select_related('sender', 'receiver'), id=delivery_id)
    if delivery.sender_id != request.organization.id and delivery.receiver_id != request.organization.id:
        messages.error(request, 'You do not have access to this delivery.')
        return redirect('delivery_list')
    if request.method != 'POST':
        return redirect('delivery_detail', delivery_id=delivery.id)
    new_status = request.POST.get('status', '').upper()
    valid = dict(Delivery.STATUS_CHOICES)
    if new_status not in valid:
        messages.error(request, 'Invalid delivery status.')
        return redirect('delivery_detail', delivery_id=delivery.id)
    workflow = {'REQUESTED': 0, 'ASSIGNED': 1, 'PICKED_UP': 2, 'IN_TRANSIT': 3, 'DELIVERED': 4, 'CANCELLED': 99}
    current_rank = workflow.get(delivery.status, 0)
    new_rank = workflow.get(new_status, 0)
    with transaction.atomic():
        delivery = Delivery.objects.select_for_update().get(id=delivery_id)
        if delivery.status == 'DELIVERED' and new_status != 'DELIVERED':
            messages.error(request, 'A delivered shipment cannot be moved back to an earlier status.')
            return redirect('delivery_detail', delivery_id=delivery.id)
        if delivery.status == 'CANCELLED' and new_status != 'CANCELLED':
            messages.error(request, 'A cancelled shipment cannot be reopened from this screen.')
            return redirect('delivery_detail', delivery_id=delivery.id)
        if new_status not in {'CANCELLED', 'DELIVERED'} and new_rank < current_rank:
            messages.error(request, 'Delivery status cannot move backwards.')
            return redirect('delivery_detail', delivery_id=delivery.id)
        
        delivery.status = new_status
        if new_status == 'DELIVERED':
            from django.utils import timezone
            delivery.delivered_at = timezone.now()
            # Increment recipient counts
            if delivery.sender:
                from ..models import OrganizationImpact
                from django.db.models import F
                impact, _ = OrganizationImpact.objects.get_or_create(organization=delivery.sender)
                OrganizationImpact.objects.filter(pk=impact.pk).update(
                    total_meals_saved=F('total_meals_saved') + delivery.quantity,
                    total_co2_reduced_kg=F('total_co2_reduced_kg') + (delivery.quantity * 2.5),
                    impact_points=F('impact_points') + (delivery.quantity * 10)
                )
        delivery.save()
        messages.success(request, f'Delivery status updated to {valid.get(new_status, new_status)}.')
    try:
        from .utils import notify_delivery_update
        notify_delivery_update(delivery)
    except Exception as e:
        pass
    return redirect('delivery_detail', delivery_id=delivery.id)

@login_required
def delivery_live_tracking(request, delivery_id):
    delivery = get_object_or_404(Delivery, id=delivery_id)
    lat = delivery.current_lat or 12.9716
    lng = delivery.current_lng or 77.5946
    return render(request, 'delivery_live_tracking.html', {'delivery': delivery, 'lat': lat, 'lng': lng})

@login_required
def delivery_proof(request, delivery_id):
    if request.method == 'POST':
        with transaction.atomic():
            delivery = get_object_or_404(Delivery.objects.select_for_update(), id=delivery_id)
            if delivery.status == 'DELIVERED':
                messages.error(request, 'This delivery is already marked as delivered.')
                return redirect('delivery_detail', delivery_id=delivery.id)

            proof_image = request.FILES.get('proof_image')
            signature = request.POST.get('recipient_signature')
            if proof_image:
                delivery.proof_image = proof_image
            if signature:
                delivery.recipient_signature = signature
            delivery.status = 'DELIVERED'
            delivery.delivered_at = timezone.now()
            delivery.save()
            
            if delivery.sender:
                from ..models import OrganizationImpact
                from django.db.models import F
                impact, _ = OrganizationImpact.objects.get_or_create(organization=delivery.sender)
                OrganizationImpact.objects.filter(pk=impact.pk).update(
                    total_meals_saved=F('total_meals_saved') + delivery.quantity,
                    total_co2_reduced_kg=F('total_co2_reduced_kg') + (delivery.quantity * 2.5),
                    impact_points=F('impact_points') + (delivery.quantity * 10)
                )
            if delivery.volunteer_driver:
                from django.db.models import F
                from ..models import VolunteerProfile
                VolunteerProfile.objects.filter(pk=delivery.volunteer_driver.pk).update(
                    total_deliveries=F('total_deliveries') + 1
                )
            
            messages.success(request, 'Proof of Delivery saved successfully!')
            return redirect('delivery_detail', delivery_id=delivery.id)
    else:
        delivery = get_object_or_404(Delivery, id=delivery_id)
        return render(request, 'delivery_proof.html', {'delivery': delivery})

@login_required
def generate_donation_receipt(request, delivery_id):
    delivery = get_object_or_404(Delivery, id=delivery_id)
    if not request.user.is_superuser:
        if delivery.sender not in request.user.organization_memberships.values_list('organization', flat=True):
            messages.error(request, 'You do not have permission to view this receipt.')
            return redirect('delivery_list')
    if delivery.status != 'DELIVERED':
        messages.error(request, 'Receipts are only available for delivered items.')
        return redirect('delivery_detail', delivery_id=delivery.id)
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    p.setFont('Helvetica-Bold', 24)
    p.setFillColor(colors.HexColor('#166534'))
    p.drawString(50, height - 80, 'Official Donation Receipt')
    p.setFont('Helvetica', 12)
    p.setFillColor(colors.black)
    p.drawString(50, height - 110, f'Receipt ID: {delivery.tracking_code}')
    p.drawString(50, height - 130, f"Date Delivered: {(delivery.delivered_at.strftime('%Y-%m-%d %H:%M') if delivery.delivered_at else 'N/A')}")
    p.setFont('Helvetica-Bold', 14)
    p.drawString(50, height - 170, 'Donor Information')
    p.setFont('Helvetica', 12)
    p.drawString(50, height - 190, f'Organization: {delivery.sender.name}')
    p.drawString(50, height - 210, f"Registration No: {delivery.sender.registration_number or 'N/A'}")
    p.drawString(50, height - 230, f'Address: {delivery.sender.address}, {delivery.sender.city}')
    p.setFont('Helvetica-Bold', 14)
    p.drawString(300, height - 170, 'Recipient Information')
    p.setFont('Helvetica', 12)
    p.drawString(300, height - 190, f'Organization: {delivery.receiver.name}')
    p.drawString(300, height - 210, f"Registration No: {delivery.receiver.registration_number or 'N/A'}")
    p.setFont('Helvetica-Bold', 14)
    p.drawString(50, height - 270, 'Donation Details')
    p.rect(50, height - 350, 500, 70)
    p.setFont('Helvetica-Bold', 12)
    p.drawString(60, height - 300, 'Item Name')
    p.drawString(400, height - 300, 'Quantity (Meals)')
    p.setFont('Helvetica', 12)
    p.drawString(60, height - 330, str(delivery.food_name))
    p.drawString(400, height - 330, str(delivery.quantity))
    p.setFont('Helvetica-Oblique', 10)
    p.drawString(50, 100, 'Thank you for your generous contribution. This receipt is automatically generated')
    p.drawString(50, 85, 'and serves as proof of your donation for tax or reporting purposes.')
    p.showPage()
    p.save()
    buffer.seek(0)
    return FileResponse(buffer, as_attachment=True, filename=f'Receipt_{delivery.tracking_code}.pdf')

@login_required
def delivery_qr_code(request, delivery_id):
    delivery = get_object_or_404(Delivery, id=delivery_id)
    scan_url = request.build_absolute_uri(f'/deliveries/{delivery.id}/scan/')
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(scan_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color='black', back_color='white')
    response = HttpResponse(content_type='image/png')
    img.save(response, 'PNG')
    return response

@login_required
def delivery_scan_qr(request, delivery_id):
    delivery = get_object_or_404(Delivery, id=delivery_id)
    if request.method == 'POST':
        if delivery.status == 'IN_TRANSIT':
            delivery.status = 'DELIVERED'
            from django.utils import timezone
            delivery.delivered_at = timezone.now()
            delivery.save(update_fields=['status', 'delivered_at'])
            messages.success(request, f'Delivery {delivery.tracking_code} marked as DELIVERED.')
            try:
                from .utils import notify_delivery_update
                notify_delivery_update(delivery)
            except Exception as e:
                pass
        elif delivery.status in ['ASSIGNED', 'REQUESTED']:
            delivery.status = 'IN_TRANSIT'
            delivery.save(update_fields=['status'])
            messages.success(request, f'Delivery {delivery.tracking_code} marked as IN TRANSIT.')
            try:
                from .utils import notify_delivery_update
                notify_delivery_update(delivery)
            except Exception as e:
                pass
        return redirect('delivery_detail', delivery_id=delivery.id)
    return render(request, 'delivery_scan.html', {'delivery': delivery})
