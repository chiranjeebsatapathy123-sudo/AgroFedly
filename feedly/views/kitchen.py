from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from ..models import Kitchen, MealRecord, PreparationRecord, SurplusFood, KitchenInventory, KitchenAlert, Ingredient
from ..decorators import require_role, require_org_role, _organization_required

@login_required
def kitchen_dashboard(request):
    kitchen = Kitchen.objects.filter(organization__members__user=request.user).first()
    if not kitchen:
        return render(request, 'kitchen/no_kitchen.html')
        
    today = timezone.now().date()
    meals_today = MealRecord.objects.filter(kitchen=kitchen, date=today)
    surplus_today = SurplusFood.objects.filter(kitchen=kitchen, created_at__date=today)
    alerts = KitchenAlert.objects.filter(kitchen=kitchen, is_resolved=False)
    
    timeline = PreparationRecord.objects.filter(kitchen=kitchen, date=today).order_by('updated_at')
    
    context = {
        'kitchen': kitchen,
        'meals': meals_today,
        'surplus': surplus_today,
        'alerts': alerts,
        'timeline': timeline
    }
    return render(request, 'kitchen/dashboard.html', context)

@login_required
def meal_planning(request):
    kitchen = Kitchen.objects.filter(organization__members__user=request.user).first()
    meals = MealRecord.objects.filter(kitchen=kitchen).order_by('-date')
    return render(request, 'kitchen/meal_planning.html', {'meals': meals})

@login_required
def production_tracking(request):
    kitchen = Kitchen.objects.filter(organization__members__user=request.user).first()
    preparations = PreparationRecord.objects.filter(kitchen=kitchen).order_by('-updated_at')
    return render(request, 'kitchen/production_tracking.html', {'preparations': preparations})

@login_required
def register_surplus(request):
    kitchen = Kitchen.objects.filter(organization__members__user=request.user).first()
    if request.method == 'POST':
        food_name = request.POST.get('food_name')
        quantity = request.POST.get('quantity')
        storage_temp = float(request.POST.get('storage_temp', 0))
        storage_hours = float(request.POST.get('storage_hours', 0))
        
        from feedly.services.food_safety import evaluate_food_safety
        
        surplus = SurplusFood.objects.create(
            kitchen=kitchen,
            organization=kitchen.organization,
            food_name=food_name,
            quantity=quantity,
            storage_temperature=storage_temp,
            storage_time_hours=storage_hours,
            status='PENDING'
        )
        
        # Mandate food safety evaluation before finalizing
        is_safe, status, alert = evaluate_food_safety(surplus, user=request.user)
        
        if not is_safe:
            messages.warning(request, f"Food safety warning: {alert}")
        else:
            messages.success(request, f"Surplus registered and evaluated as SAFE.")
            
        return redirect('kitchen_redistribution')
    return render(request, 'kitchen/register_surplus.html')

@login_required
def redistribution_queue(request):
    kitchen = Kitchen.objects.filter(organization__members__user=request.user).first()
    surplus = SurplusFood.objects.filter(kitchen=kitchen).order_by('-created_at')
    
    # Kanban columns aligned with food_safety and matching AI modules
    columns = {
        'draft': surplus.filter(status='PENDING'),
        'safety': surplus.filter(status='SAFE', quantity__gt=0),
        'matched': surplus.filter(redistributions__isnull=False).distinct(),
        'delivered': surplus.filter(status='REDISTRIBUTED'),
    }
    return render(request, 'kitchen/redistribution_queue.html', {'columns': columns})

@login_required
def inventory(request):
    kitchen = Kitchen.objects.filter(organization__members__user=request.user).first()
    items = KitchenInventory.objects.filter(kitchen=kitchen)
    return render(request, 'kitchen/inventory.html', {'items': items})

@login_required
def kitchen_analytics(request):
    """Kitchen Intelligence Center - compares Historical vs Expected Demand."""
    from ..models import DemandForecast, MealRecord, Kitchen
    from django.db.models import Sum
    from django.utils import timezone
    
    kitchen = Kitchen.objects.filter(organization__members__user=request.user).first()
    org = kitchen.organization if kitchen else None
    
    historical = MealRecord.objects.filter(organization=org).aggregate(total=Sum('quantity'))['total'] or 0
    expected = DemandForecast.objects.filter(organization=org, target_date__gte=timezone.now().date()).aggregate(total=Sum('predicted_demand'))['total'] or 0
    
    context = {
        'kitchen': kitchen,
        'historical_demand': historical,
        'expected_demand': expected,
        'deviation': abs(expected - historical) if expected and historical else 0,
        'trend': 'UP' if expected > historical else 'DOWN'
    }
    return render(request, 'kitchen/analytics.html', context)

@login_required
@_organization_required
def waste_prevention_center(request):
    """Dashboard to analyze and prevent food waste."""
    from feedly.models import KitchenInventory, SurplusFood, MealRecord
    from django.utils import timezone
    from datetime import timedelta
    
    # 1. Expiring / Expired Inventory
    now = timezone.now()
    expiring = KitchenInventory.objects.filter(
        kitchen__organization=request.organization,
        expiry_date__lte=now + timedelta(days=2),
        quantity__gt=0
    )
    
    # 2. Rejected/Unsafe Surplus
    unsafe_surplus = SurplusFood.objects.filter(
        organization=request.organization,
        status='UNSAFE'
    ).order_by('-created_at')[:10]
    
    context = {
        'expiring_inventory': expiring,
        'unsafe_surplus': unsafe_surplus,
    }
    return render(request, 'kitchen/waste_prevention_center.html', context)

@login_required
@_organization_required
def preparation_optimizer(request):
    """Workflow mapping forecast to prep, with human approval."""
    from feedly.models import DemandForecast, AIRecommendation
    from django.utils import timezone
    
    # Simple forecast pull
    forecasts = DemandForecast.objects.filter(
        organization=request.organization,
        target_date__gte=timezone.now().date()
    ).order_by('target_date')[:5]
    
    # Mock some recommendations for UI mapping
    recommendations = AIRecommendation.objects.filter(
        organization=request.organization,
        category='PREPARATION',
        status='NEW'
    )
    
    context = {
        'forecasts': forecasts,
        'recommendations': recommendations
    }
    return render(request, 'kitchen/preparation_optimizer.html', context)
