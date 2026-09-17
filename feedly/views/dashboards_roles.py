from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from ..decorators import require_farmer, require_fpo, require_agribusiness, require_officer, require_ngo, require_researcher
from django.db.models import Sum, Q, F
from ..models import Farm, CropYieldPrediction, CropDiseaseScan, WeatherAdvisory, CropMarketTrend, AgriculturalProduce, FarmEvent, FarmInput
from ..models import OrganizationMember, AgriculturalSupplyRequest, Delivery, BuyerDemand, SurplusFood, Recipient
from ..ai.advisor import calculate_farm_health_score

@login_required
@require_farmer
def dashboard_farmer(request):
    """Phase 6: Farmer Dashboard -> Smart Farm Command Center"""
    farms = Farm.objects.filter(owner=request.user)
    
    # Calculate Farm Health Score for the primary farm
    primary_farm = farms.first()
    farm_health = calculate_farm_health_score(primary_farm) if primary_farm else {"score": None, "status": "No Farm", "factors": []}
    
    # Weather
    weather_alerts = WeatherAdvisory.objects.order_by('-issued_at')[:3]
    
    # AI Status
    recent_scans = CropDiseaseScan.objects.filter(farmer=request.user).order_by('-scanned_at')[:3]
    recent_yields = CropYieldPrediction.objects.filter(farmer=request.user).order_by('-created_at')[:3]
    
    # Operations
    today_tasks = FarmEvent.objects.filter(farm__owner=request.user, is_completed=False).order_by('date')[:5]
    
    # Market
    market_trends = CropMarketTrend.objects.order_by('-record_date')[:5]
    
    # Inventory
    low_stock_inputs = FarmInput.objects.filter(farm__owner=request.user, quantity__lte=F('low_stock_threshold'))

    context = {
        'farms': farms,
        'primary_farm': primary_farm,
        'farm_health': farm_health,
        'today_tasks': today_tasks,
        'market_trends': market_trends,
        'low_stock_inputs': low_stock_inputs,
        'recent_scans': recent_scans,
        'recent_yields': recent_yields,
        'weather_alerts': weather_alerts,
        'role': 'FARMER'
    }
    return render(request, 'dashboards/farmer.html', context)

@login_required
@require_fpo
def dashboard_fpo(request):
    """Phase 12: FPO Dashboard"""
    org = request.user.organization_memberships.first().organization
    members = OrganizationMember.objects.filter(organization=org)
    total_farmers = members.count()
    
    produce = AgriculturalProduce.objects.filter(supplier=org)
    available_stock = produce.aggregate(total=Sum('available_quantity'))['total'] or 0
    
    active_orders = AgriculturalSupplyRequest.objects.filter(produce__supplier=org).exclude(status__in=['DELIVERED', 'CANCELLED'])
    recent_deliveries = Delivery.objects.filter(Q(sender=org) | Q(receiver=org)).order_by('-created_at')[:5]
    
    context = {
        'total_farmers': total_farmers,
        'available_stock': available_stock,
        'active_orders': active_orders,
        'recent_deliveries': recent_deliveries,
        'members': members[:10],
        'role': 'FPO'
    }
    return render(request, 'dashboards/fpo.html', context)

@login_required
@require_agribusiness
def dashboard_agribusiness(request):
    """Phase 11: Buyer / Agribusiness Dashboard"""
    org = request.user.organization_memberships.first().organization
    
    purchase_requirements = BuyerDemand.objects.filter(organization=org)
    available_produce = AgriculturalProduce.objects.filter(available_quantity__gt=0).order_by('-harvest_date')[:10]
    active_orders = AgriculturalSupplyRequest.objects.filter(requester=org).exclude(status__in=['DELIVERED', 'CANCELLED'])
    delivery_pipeline = Delivery.objects.filter(receiver=org, status__in=['REQUESTED', 'IN_TRANSIT', 'PICKED_UP', 'ASSIGNED'])
    market_info = CropMarketTrend.objects.order_by('-record_date')[:5]
    
    context = {
        'purchase_requirements': purchase_requirements,
        'available_produce': available_produce,
        'active_orders': active_orders,
        'delivery_pipeline': delivery_pipeline,
        'market_info': market_info,
        'role': 'AGRIBUSINESS'
    }
    return render(request, 'dashboards/agribusiness.html', context)

@login_required
@require_officer
def dashboard_officer(request):
    """Phase 13: Agriculture Officer Dashboard"""
    farms = Farm.objects.all().count()
    alerts = WeatherAdvisory.objects.order_by('-issued_at')[:5]
    
    context = {
        'total_registered_farms': farms,
        'alerts': alerts,
        'role': 'OFFICER'
    }
    return render(request, 'dashboards/officer.html', context)

@login_required
@require_ngo
def dashboard_ngo(request):
    """Phase 14: NGO Dashboard"""
    org = request.user.organization_memberships.first().organization
    
    available_surplus = SurplusFood.objects.filter(status='SAFE', quantity__gt=0)
    verification_queue = SurplusFood.objects.filter(status='PENDING')
    recipients = Recipient.objects.filter(organization=org)
    deliveries = Delivery.objects.filter(sender=org).order_by('-created_at')[:5]
    
    context = {
        'available_surplus': available_surplus,
        'verification_queue': verification_queue,
        'recipients': recipients,
        'deliveries': deliveries,
        'role': 'NGO'
    }
    return render(request, 'dashboards/ngo.html', context)

@login_required
@require_researcher
def dashboard_researcher(request):
    """Phase 1: Researcher Dashboard"""
    context = {'role': 'RESEARCHER'}
    return render(request, 'dashboards/researcher.html', context)
