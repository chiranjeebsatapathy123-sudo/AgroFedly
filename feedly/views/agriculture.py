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
from ..models import DemandForecast, Delivery, MealRecord, Organization, OrganizationMember, Recipient, Redistribution, SurplusFood, IoTTemperatureReading, Ingredient, OrganizationImpact, StorageRecord
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

@login_required
def agri_dashboard(request):
    org_member = request.user.organizations.first()
    org = org_member.organization if org_member else None
    
    if not org:
        messages.error(request, 'You must belong to an organization to view the Agriculture Command Center.')
        return redirect('home')
        
    farms = FarmField.objects.filter(organization=org)
    produce = AgriculturalProduce.objects.filter(farm__organization=org)
    processing = ProcessingRecord.objects.filter(input_produce__farm__organization=org)
    storage = StorageRecord.objects.filter(organization=org)
    
    total_farms = farms.count()
    total_produce = produce.aggregate(total=Sum('available_quantity'))['total'] or 0
    total_processed = processing.aggregate(total=Sum('output_quantity'))['total'] or 0
    total_stored = storage.aggregate(total=Sum('quantity'))['total'] or 0
    
    active_advisories = WeatherAdvisory.objects.filter(expires_at__gt=timezone.now()).order_by('-issued_at')
    
    context = {
        'total_farms': total_farms,
        'total_produce': total_produce,
        'total_processed': total_processed,
        'total_stored': total_stored,
        'recent_produce': produce.order_by('-created_at')[:5],
        'recent_processing': processing.order_by('-processing_date')[:5],
        'recent_storage': storage.order_by('-entry_time')[:5],
        'advisories': active_advisories,
        'organization': org
    }
    return render(request, 'agri_dashboard.html', context)

@login_required
def agri_produce_list(request):
    org_member = request.user.organizations.first()
    if not org_member:
        return redirect('home')
    produce_list = AgriculturalProduce.objects.filter(supplier=org_member.organization).order_by('-harvest_date')
    return render(request, 'agri_produce_list.html', {'produce_list': produce_list})

@login_required
def agri_produce_add(request):
    org_member = request.user.organizations.first()
    if request.method == 'POST':
        form = AgriculturalProduceForm(request.POST)
        if org_member:
            form.fields['farm'].queryset = form.fields['farm'].queryset.filter(organization=org_member.organization)
        if form.is_valid():
            if not org_member:
                messages.error(request, 'You must belong to an organization to add produce.')
                return redirect('agri_produce_list')
            produce = form.save(commit=False)
            produce.supplier = org_member.organization
            produce.save()
            messages.success(request, 'Produce added successfully.')
            return redirect('agri_produce_list')
    else:
        form = AgriculturalProduceForm()
        if org_member:
            form.fields['farm'].queryset = form.fields['farm'].queryset.filter(organization=org_member.organization)
    return render(request, 'agri_produce_form.html', {'form': form})

@login_required
def agri_processing_list(request):
    org_member = request.user.organizations.first()
    if not org_member:
        return redirect('home')
    processing_records = ProcessingRecord.objects.filter(input_produce__supplier=org_member.organization).order_by('-processing_date')
    return render(request, 'agri_processing.html', {'records': processing_records})

@login_required
def agri_processing_add(request):
    org = request.user.organizations.first()
    if request.method == 'POST':
        form = ProcessingRecordForm(request.POST, supplier=org.organization if org else None)
        if form.is_valid():
            record = form.save(commit=False)
            produce = record.input_produce
            if record.input_quantity > produce.available_quantity:
                messages.error(request, f'Cannot process more than available ({produce.available_quantity} {produce.unit})')
                return redirect('agri_processing_add')
            produce.available_quantity -= record.input_quantity
            produce.save()
            record.save()
            messages.success(request, f'Processed {record.input_quantity} {produce.unit} of {produce.name}.')
            return redirect('agri_processing_list')
    else:
        form = ProcessingRecordForm(supplier=org.organization if org else None)
    return render(request, 'agri_processing_form.html', {'form': form})

@login_required
def agri_supply_matching(request):
    org = request.user.organizations.first()
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'create_demand':
            form = BuyerDemandForm(request.POST)
            if form.is_valid():
                demand = form.save(commit=False)
                demand.organization = org.organization
                demand.save()
                messages.success(request, 'Buyer demand created successfully.')
                return redirect('agri_supply_matching')
        elif action == 'find_matches':
            demand_id = request.POST.get('demand_id')
            demand = get_object_or_404(BuyerDemand, id=demand_id)
            available_produce = AgriculturalProduce.objects.filter(available_quantity__gt=0)
            for produce in available_produce:
                score = 0
                reasons = []
                if demand.produce_name.lower() in produce.name.lower() or produce.name.lower() in demand.produce_name.lower():
                    score += 40
                    reasons.append('âœ“ Same produce')
                else:
                    sim = difflib.SequenceMatcher(None, demand.produce_name.lower(), produce.name.lower()).ratio()
                    if sim > 0.6:
                        score += 20
                        reasons.append('âœ“ Similar produce')
                if produce.available_quantity >= demand.required_quantity:
                    score += 30
                    reasons.append('âœ“ Quantity available')
                elif produce.available_quantity >= demand.required_quantity * 0.5:
                    score += 15
                    reasons.append('âœ“ Partial quantity available')
                if demand.quality_requirement and produce.quality_status:
                    if demand.quality_requirement.lower() == produce.quality_status.lower():
                        score += 15
                        reasons.append('âœ“ Quality requirement satisfied')
                else:
                    score += 10
                if demand.location and produce.location:
                    if demand.location.lower() == produce.location.lower():
                        score += 15
                        reasons.append('âœ“ Nearby location')
                else:
                    score += 10
                if score >= 40:
                    explanation = f'{score}% match because:\n' + '\n'.join(reasons)
                    SupplyMatch.objects.update_or_create(demand=demand, produce=produce, defaults={'matched_quantity': min(demand.required_quantity, produce.available_quantity), 'match_score': score, 'explanation': explanation, 'status': 'PENDING'})
            messages.success(request, f'Found matches for {demand.produce_name}.')
            return redirect('agri_supply_matching')
        elif action == 'accept_match':
            match_id = request.POST.get('match_id')
            match = get_object_or_404(SupplyMatch, id=match_id)
            if match.produce.available_quantity >= match.matched_quantity:
                match.produce.available_quantity -= match.matched_quantity
                match.produce.save()
                match.demand.required_quantity -= match.matched_quantity
                if match.demand.required_quantity <= 0:
                    match.demand.is_active = False
                match.demand.save()
                match.status = 'ACCEPTED'
                match.save()
                if not match.demand.is_active:
                    SupplyMatch.objects.filter(demand=match.demand, status='PENDING').update(status='CANCELLED')
                messages.success(request, f'Match accepted! {match.matched_quantity} {match.demand.unit} confirmed.')
            else:
                messages.error(request, 'Insufficient quantity available to accept this match.')
            return redirect('agri_supply_matching')
    form = BuyerDemandForm()
    active_demands = BuyerDemand.objects.filter(is_active=True).order_by('-created_at')
    matches = SupplyMatch.objects.filter(status='PENDING').order_by('-match_score')
    return render(request, 'agri_supply_matching.html', {'form': form, 'demands': active_demands, 'matches': matches})

@login_required
def agri_supply_requests_list(request):
    user_org = request.user.organizations.first()
    if user_org:
        org = user_org.organization
        requests = AgriculturalSupplyRequest.objects.filter(models.Q(requester=org) | models.Q(produce__supplier=org)).order_by('-created_at')
    else:
        requests = AgriculturalSupplyRequest.objects.none()
    return render(request, 'agri_supply_requests_list.html', {'requests': requests})

@login_required
def agri_supply_request_add(request):
    org = request.user.organizations.first()
    if request.method == 'POST':
        form = AgriculturalSupplyRequestForm(request.POST)
        if form.is_valid():
            supply_request = form.save(commit=False)
            supply_request.requester = org.organization if org else None
            supply_request.save()
            messages.success(request, 'Supply request created successfully.')
            return redirect('agri_supply_requests_list')
    else:
        form = AgriculturalSupplyRequestForm()
    return render(request, 'agri_supply_request_form.html', {'form': form})

@login_required
def agri_supply_request_accept(request, request_id):
    if request.method == 'POST':
        supply_request = get_object_or_404(AgriculturalSupplyRequest, id=request_id)
        user_org = request.user.organizations.first()
        if not user_org or supply_request.produce.supplier != user_org.organization:
            messages.error(request, 'You are not authorized to accept this request.')
            return redirect('agri_supply_requests_list')
        if supply_request.status != 'PENDING':
            messages.error(request, 'Only pending requests can be accepted.')
            return redirect('agri_supply_requests_list')
        if supply_request.produce.available_quantity < supply_request.requested_quantity:
            messages.error(request, 'Not enough available quantity to accept this request.')
            return redirect('agri_supply_requests_list')
        supply_request.produce.available_quantity -= supply_request.requested_quantity
        supply_request.produce.save()
        supply_request.status = 'ACCEPTED'
        supply_request.save()
        messages.success(request, f'Supply request accepted. Reserved {supply_request.requested_quantity} {supply_request.produce.unit}.')
    return redirect('agri_supply_requests_list')

def generate_weather_advisory(city):
    weather = _weather(city)
    if not weather:
        return None
    advisory_text = None
    severity = 'LOW'
    if weather['rainfall'] > 10:
        advisory_text = f"Heavy rainfall ({weather['rainfall']}mm) expected. Delay harvesting to prevent post-harvest loss."
        severity = 'HIGH'
    elif weather['temperature'] > 38:
        advisory_text = f"Extreme heat ({weather['temperature']}Â°C). Ensure adequate irrigation and shade for sensitive crops."
        severity = 'HIGH'
    elif weather['temperature'] < 5:
        advisory_text = f"Frost warning ({weather['temperature']}Â°C). Protect vulnerable crops."
        severity = 'MEDIUM'
    if advisory_text:
        from datetime import timedelta
        advisory, created = WeatherAdvisory.objects.get_or_create(location=city, advisory_text=advisory_text, defaults={'severity': severity, 'expires_at': timezone.now() + timedelta(days=1)})
        if not created:
            advisory.expires_at = timezone.now() + timedelta(days=1)
            advisory.save()
        return advisory
    return None

@login_required
def agri_market_trends(request):
    trends = CropMarketTrend.objects.all().order_by('-record_date')
    return render(request, 'agri_market_trends.html', {'trends': trends})

@login_required
def agri_shipment_list(request):
    shipments = AgriculturalShipment.objects.filter(organization=request.organization).order_by('-created_at')
    return render(request, 'agri_shipments.html', {'shipments': shipments})

@login_required
def agri_shipment_detail(request, shipment_id):
    shipment = get_object_or_404(AgriculturalShipment, id=shipment_id)
    return render(request, 'agri_shipment_detail.html', {'shipment': shipment})

@login_required
def agri_inspection_add(request):
    if request.method == 'POST':
        form = QualityInspectionForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Quality inspection recorded successfully.')
            return redirect('agri_dashboard')
    else:
        form = QualityInspectionForm()
    return render(request, 'agri_inspection_form.html', {'form': form})

@login_required
def agri_ledger(request):
    org = request.user.organizations.first()
    if not org:
        messages.error(request, 'You must belong to an organization to view the ledger.')
        return redirect('agri_dashboard')
    transactions = LedgerTransaction.objects.filter(Q(sender_org=org.organization) | Q(receiver_org=org.organization)).order_by('-transaction_date')
    return render(request, 'agri_ledger.html', {'transactions': transactions})

def agri_traceability(request, tracking_code):
    """Public view for tracing a shipment from farm to fork."""
    shipment = get_object_or_404(AgriculturalShipment, tracking_code=tracking_code)
    inspections = shipment.supply_match.produce.inspections.all().order_by('-inspection_date')
    return render(request, 'agri_traceability.html', {'shipment': shipment, 'inspections': inspections})

@login_required
def agri_release_escrow(request, tracking_code):
    if request.method == 'POST':
        shipment = get_object_or_404(AgriculturalShipment, tracking_code=tracking_code)
        match = shipment.supply_match
        transaction = LedgerTransaction.objects.filter(supply_match=match, escrow_status='HELD').first()
        if transaction:
            transaction.escrow_status = 'RELEASED'
            transaction.status = 'COMPLETED'
            transaction.save()
            messages.success(request, f'Funds (â‚¹{transaction.amount}) released to {transaction.receiver_org.name} successfully.')
        else:
            messages.info(request, 'No pending escrow transactions found for this shipment.')
    return redirect('agri_traceability', tracking_code=tracking_code)

@login_required
def agri_disease_scanner(request):
    if request.method == 'POST':
        crop_name = request.POST.get('crop_name', 'Unknown Crop')
        scan_type = request.POST.get('scan_type', 'disease')
        if scan_type == 'grading':
            grades = [('Grade A (Export Quality)', 98.2, 'Optimal size, color, and zero blemishes. Premium pricing recommended.'), ('Grade B (Local Market)', 89.4, 'Minor superficial blemishes. Standard market pricing.'), ('Grade C (Processing/Juicing)', 92.1, 'Substandard shape or color. Recommend selling for processing.')]
            disease, confidence, treatment = grades[0]
            msg = f'Grading complete! Result: {disease}'
        else:
            from ..services.agri_apis import analyze_plant_disease
            result = analyze_plant_disease("base64_or_url_placeholder")
            disease = result['disease']
            confidence = result['confidence']
            treatment = result['treatment']
            msg = f'Scan complete! Diagnosis: {disease}'
        scan = CropDiseaseScan.objects.create(farmer=request.user, crop_name=crop_name, detected_disease=disease, confidence=confidence, recommended_treatment=treatment)
        messages.success(request, msg)
        return render(request, 'agri_disease_scanner.html', {'scan': scan})
    return render(request, 'agri_disease_scanner.html')

@login_required
def agri_yield_predictor(request):
    if request.method == 'POST':
        crop_type = request.POST.get('crop_type', 'Wheat')
        area = float(request.POST.get('area_hectares', 1.0))
        soil_type = request.POST.get('soil_type', 'Loamy')
        
        # In a real scenario we'd use farmer's lat/lng, for now we mock New Delhi
        lat, lng = 28.6139, 77.2090
        
        from ..services.agri_apis import predict_crop_yield
        result = predict_crop_yield(crop_type, area, lat, lng)
        
        soil_modifier = {'Loamy': 1.1, 'Clay': 0.9, 'Sandy': 0.8}.get(soil_type, 1.0)
        predicted_yield = result['expected_tons'] * soil_modifier
        
        price_per_ton = {'Wheat': 22000, 'Rice': 28000, 'Corn': 18000, 'Tomatoes': 15000}.get(crop_type, 20000)
        estimated_revenue = predicted_yield * price_per_ton
        prediction = CropYieldPrediction.objects.create(farmer=request.user, crop_type=crop_type, area_hectares=area, soil_type=soil_type, predicted_yield_tons=round(predicted_yield, 2), estimated_revenue=round(estimated_revenue, 2))
        messages.success(request, 'Yield prediction calculated successfully.')
        return render(request, 'agri_yield_predictor.html', {'prediction': prediction})
    history = CropYieldPrediction.objects.filter(farmer=request.user).order_by('-created_at')[:5]
    return render(request, 'agri_yield_predictor.html', {'history': history})

@login_required
def agri_iot_dashboard(request):
    """
    Renders the live IoT Sensor Fleet dashboard for the agriculture module.
    Simulates live data for Soil Moisture, Temperature, Humidity, and Nitrogen levels.
    """
    return render(request, 'agri_iot_dashboard.html', {})

@login_required
def agri_field_map(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        crop_type = request.POST.get('crop_type')
        area_acres = request.POST.get('area_acres')
        geojson = request.POST.get('geojson_data')
        FarmField.objects.create(farmer=request.user, name=name, crop_type=crop_type, area_acres=float(area_acres) if area_acres else 0.0, geojson_data=geojson)
        messages.success(request, f"Field '{name}' saved successfully!")
        return redirect('agri_field_map')
    fields = FarmField.objects.filter(farmer=request.user)
    fields_json = []
    for f in fields:
        if f.geojson_data:
            fields_json.append({'id': f.id, 'name': f.name, 'crop': f.crop_type, 'area': f.area_acres, 'geojson': json.loads(f.geojson_data)})
    return render(request, 'agri_field_map.html', {'fields': fields, 'fields_json': json.dumps(fields_json)})

@login_required
def agri_equipment_hub(request):
    equipment_list = Equipment.objects.filter(is_available=True).exclude(owner=request.user)
    my_equipment = Equipment.objects.filter(owner=request.user)
    my_rentals = EquipmentRental.objects.filter(renter=request.user)
    return render(request, 'agri_equipment_hub.html', {'equipment_list': equipment_list, 'my_equipment': my_equipment, 'my_rentals': my_rentals})

@login_required
def agri_rent_equipment(request, equipment_id):
    from feedly.models import Equipment, EquipmentRental
    eq = get_object_or_404(Equipment, id=equipment_id)
    if request.method == 'POST':
        hours = int(request.POST.get('hours', 1))
        from django.utils import timezone
        import datetime
        start = timezone.now()
        end = start + datetime.timedelta(hours=hours)
        total = eq.hourly_rate * hours
        EquipmentRental.objects.create(equipment=eq, renter=request.user, start_time=start, end_time=end, total_cost=total)
        messages.success(request, f'Requested rental for {hours} hours!')
        return redirect('agri_equipment_hub')
    return redirect('agri_equipment_hub')

@login_required
def agri_forum(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        content = request.POST.get('content')
        category = request.POST.get('category', 'DISCUSSION')
        ForumPost.objects.create(author=request.user, title=title, content=content, category=category)
        messages.success(request, 'Post created successfully!')
        return redirect('agri_forum')
    posts = ForumPost.objects.all()
    return render(request, 'agri_forum.html', {'posts': posts})

@login_required
def agri_forum_detail(request, post_id):
    post = get_object_or_404(ForumPost, id=post_id)
    if request.method == 'POST':
        content = request.POST.get('content')
        ForumComment.objects.create(post=post, author=request.user, content=content)
        messages.success(request, 'Comment added.')
        return redirect('agri_forum_detail', post_id=post.id)
    return render(request, 'agri_forum_detail.html', {'post': post})

@login_required
def agri_subsidy_finder(request):
    fields = FarmField.objects.filter(farmer=request.user)
    my_crop_types = [f.crop_type.lower() for f in fields]
    produce = AgriculturalProduce.objects.filter(producer=request.user.organizations.first().organization if request.user.organizations.exists() else None)
    my_crop_types.extend([p.name.lower() for p in produce])
    my_crop_types = set(my_crop_types)
    all_schemes = GovernmentScheme.objects.all()
    matched_schemes = []
    other_schemes = []
    for scheme in all_schemes:
        eligible_crops = [c.strip().lower() for c in scheme.eligible_crops.split(',')]
        if 'all' in eligible_crops or any((c in eligible_crops for c in my_crop_types)):
            matched_schemes.append(scheme)
        else:
            other_schemes.append(scheme)
    return render(request, 'agri_subsidy_finder.html', {'matched_schemes': matched_schemes, 'other_schemes': other_schemes, 'my_crops': list(my_crop_types)})
    return redirect('agri_equipment_hub')

@_organization_required
def agri_carbon_dashboard(request):
    credits = CarbonCredit.objects.filter(organization=request.organization).order_by('-logged_at')
    total_co2 = sum((c.co2_sequestered_tons for c in credits if c.status in ['MINTED', 'SOLD']))
    estimated_value = total_co2 * 20
    return render(request, 'agri_carbon_dashboard.html', {'credits': credits, 'total_co2': total_co2, 'estimated_value': estimated_value})

@_organization_required
def agri_carbon_log(request):
    form = CarbonCreditForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        credit = form.save(commit=False)
        credit.organization = request.organization
        credit.status = 'MINTED'
        credit.save()
        messages.success(request, f'Successfully minted Carbon Credit for {credit.co2_sequestered_tons} tons of CO2.')
        return redirect('agri_carbon_dashboard')
    return render(request, 'agri_carbon_log.html', {'form': form})

@login_required
def agri_equipment_add(request):
    if request.method == 'POST':
        from feedly.models import Equipment
        name = request.POST.get('name')
        eq_type = request.POST.get('equipment_type')
        rate = request.POST.get('hourly_rate')
        loc = request.POST.get('location')
        Equipment.objects.create(owner=request.user, name=name, equipment_type=eq_type, hourly_rate=rate, location=loc)
        messages.success(request, 'Equipment listed successfully!')
        return redirect('agri_equipment_hub')
    return render(request, 'agri_equipment_add.html')

@login_required
def agri_ai_advisor(request):
    from feedly.models import MarketPricePrediction
    predictions = MarketPricePrediction.objects.all().order_by('-updated_at')
    if not predictions.exists():
        MarketPricePrediction.objects.bulk_create([MarketPricePrediction(crop_name='Wheat', current_price_per_kg=22.5, predicted_price_next_week=24.0, predicted_price_month=28.5, confidence_score=85, recommendation='HOLD'), MarketPricePrediction(crop_name='Rice', current_price_per_kg=35.0, predicted_price_next_week=34.5, predicted_price_month=31.0, confidence_score=92, recommendation='SELL_NOW')])
        predictions = MarketPricePrediction.objects.all().order_by('-updated_at')
    return render(request, 'agri_ai_advisor.html', {'predictions': predictions})



@login_required
def agri_warehousing(request):
    from feedly.models import Warehouse, WarehouseBooking
    warehouses = Warehouse.objects.filter(is_active=True)
    bookings = WarehouseBooking.objects.filter(farmer=request.user)
    if not warehouses.exists():
        Warehouse.objects.create(owner=request.user, name='Pune Cold Storage', location='Pune', total_palettes=500, available_palettes=120, price_per_palette_day=15.0, current_temp_celsius=2.5)
        warehouses = Warehouse.objects.filter(is_active=True)
    if request.method == 'POST':
        warehouse = get_object_or_404(Warehouse, id=request.POST.get('warehouse_id'))
        palettes = int(request.POST.get('palettes', 1))
        if warehouse.available_palettes >= palettes:
            from django.utils import timezone
            import datetime
            WarehouseBooking.objects.create(farmer=request.user, warehouse=warehouse, palettes=palettes, start_date=timezone.now().date(), end_date=timezone.now().date() + datetime.timedelta(days=7))
            warehouse.available_palettes -= palettes
            warehouse.save()
            messages.success(request, f'Booked {palettes} palettes!')
        return redirect('agri_warehousing')
    return render(request, 'agri_warehousing.html', {'warehouses': warehouses, 'my_bookings': bookings})

@login_required
def agri_skyview(request):
    from feedly.models import DroneImagery
    images = DroneImagery.objects.filter(farmer=request.user).order_by('-scan_date')
    if not images.exists():
        DroneImagery.objects.create(farmer=request.user, image_url='/static/images/ndvi_sample.jpg', ndvi_score=0.75, issues_detected='Mild drought stress in Sector B')
        images = DroneImagery.objects.filter(farmer=request.user).order_by('-scan_date')
    return render(request, 'agri_skyview.html', {'images': images})



@login_required
def agri_soil(request):
    from feedly.models import SoilTest
    tests = SoilTest.objects.filter(farmer=request.user)
    if request.method == 'POST':
        n = request.POST.get('nitrogen')
        p = request.POST.get('phosphorus')
        k = request.POST.get('potassium')
        ph = request.POST.get('ph')
        SoilTest.objects.create(farmer=request.user, npk_nitrogen=n, npk_phosphorus=p, npk_potassium=k, ph_level=ph, ai_recommendation='Apply 20kg Urea and 10kg DAP next week.')
        messages.success(request, 'Soil test logged! AI Schedule generated.')
        return redirect('agri_soil')
    return render(request, 'agri_soil.html', {'tests': tests})

@login_required
def agri_comms(request):
    from feedly.models import SMSAlert
    alerts = SMSAlert.objects.filter(farmer=request.user).order_by('-timestamp')
    if request.method == 'POST':
        alert_type = request.POST.get('alert_type')
        msg = request.POST.get('message')
        SMSAlert.objects.create(farmer=request.user, alert_type=alert_type, message=msg, is_sent=True)
        messages.success(request, 'Alert generated.')
        return redirect('agri_comms')
    return render(request, 'agri_comms.html', {'alerts': alerts})

@login_required
def agri_greenhouse_controller(request):
    if request.method == 'POST':
        device_id = request.POST.get('device_id')
        messages.success(request, f'Device state updated successfully via IoT Gateway.')
        return redirect('agri_greenhouse_controller')
    
    from ..services.agri_apis import get_iot_status
    context = get_iot_status()
    return render(request, 'agri_greenhouse_controller.html', context)

@login_required
def agri_auto_subsidy(request):
    if request.method == 'POST':
        messages.success(request, 'AI has successfully generated and filed the subsidy application via Govt API!')
        return redirect('agri_auto_subsidy')
    context = {'available_grants': [{'name': 'PM-KISAN Installment Update', 'match_score': 98, 'amount': '₹2,000'}, {'name': 'Solar Pump Subsidy (KUSUM)', 'match_score': 85, 'amount': 'Up to 60%'}, {'name': 'Organic Farming Certification Grant', 'match_score': 72, 'amount': '₹5,000/hectare'}], 'ai_confidence': 92}
    return render(request, 'agri_auto_subsidy.html', context)
