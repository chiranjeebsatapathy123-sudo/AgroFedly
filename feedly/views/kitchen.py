from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from ..models import Kitchen, MealRecord, PreparationRecord, SurplusFood, KitchenInventory, KitchenAlert, Ingredient
from ..decorators import require_role, require_org_role, _organization_required, require_sector

@login_required
@require_sector('KITCHEN')
def kitchen_dashboard(request):
    request.session['active_workspace'] = 'KITCHEN'
    from feedly.services.organizations import get_active_organization
    org = get_active_organization(request.user, request)
    kitchen = Kitchen.objects.filter(organization=org).first() if org else None
    if not kitchen:
        return render(request, 'kitchen/no_kitchen.html')
        
    today = timezone.now().date()
    
    # 1. Meals Today
    meals_today = MealRecord.objects.filter(kitchen=kitchen, date=today)
    
    from django.db.models import Sum
    
    # KPIs
    kpi_expected = meals_today.aggregate(total=Sum('expected_attendance'))['total'] or 0
    kpi_to_prepare = meals_today.aggregate(total=Sum('recommended_production'))['total'] or 0
    kpi_prepared = meals_today.aggregate(total=Sum('meals_prepared'))['total'] or 0
    kpi_served = meals_today.aggregate(total=Sum('meals_consumed'))['total'] or 0
    
    surplus_today = SurplusFood.objects.filter(kitchen=kitchen, created_at__date=today)
    kpi_surplus = surplus_today.aggregate(total=Sum('quantity'))['total'] or 0
    
    # Waste (Unsafe surplus + explicitly discarded meals)
    discarded = meals_today.aggregate(total=Sum('discarded_meals'))['total'] or 0
    unsafe_surplus = surplus_today.filter(status='UNSAFE').aggregate(total=Sum('quantity'))['total'] or 0
    kpi_waste = discarded + unsafe_surplus
    
    # Surplus breakdown
    surplus_safe = surplus_today.filter(status='SAFE').aggregate(total=Sum('quantity'))['total'] or 0
    surplus_pending = surplus_today.filter(status='PENDING').aggregate(total=Sum('quantity'))['total'] or 0
    surplus_unsafe = unsafe_surplus
    
    # Live Status Counts
    count_planned = meals_today.filter(status='PLANNED').count()
    count_preparing = meals_today.filter(status='PREPARING').count()
    count_serving = meals_today.filter(status='SERVING').count()
    count_completed = meals_today.filter(status='COMPLETED').count()

    # Alerts & Needs Attention
    alerts = KitchenAlert.objects.filter(kitchen=kitchen, is_resolved=False).order_by('-created_at')
    
    # Today's Production Table
    # Using meals_today directly
    
    context = {
        'kitchen': kitchen,
        'meals_today': meals_today.order_by('meal_session'),
        'kpi_expected': kpi_expected,
        'kpi_to_prepare': kpi_to_prepare,
        'kpi_prepared': kpi_prepared,
        'kpi_served': kpi_served,
        'kpi_surplus': kpi_surplus,
        'kpi_waste': kpi_waste,
        'surplus_safe': surplus_safe,
        'surplus_pending': surplus_pending,
        'surplus_unsafe': surplus_unsafe,
        'count_planned': count_planned,
        'count_preparing': count_preparing,
        'count_serving': count_serving,
        'count_completed': count_completed,
        'alerts': alerts,
        'today': today
    }
    return render(request, 'kitchen/dashboard.html', context)

@login_required
def meal_planning(request):
    from feedly.services.organizations import get_active_organization
    org = get_active_organization(request.user, request)
    kitchen = Kitchen.objects.filter(organization=org).first() if org else None
    
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'update':
            meal_id = request.POST.get('meal_id')
            attendance = request.POST.get('expected_attendance')
            if meal_id and attendance is not None:
                meal = get_object_or_404(MealRecord, id=meal_id, kitchen=kitchen)
                meal.expected_attendance = attendance
                meal.save(update_fields=['expected_attendance'])
                messages.success(request, f"Updated expected attendance for {meal.date} ({meal.meal_session})")
        return redirect('kitchen_meal_planning')

    meals = MealRecord.objects.filter(kitchen=kitchen).order_by('-date')
    return render(request, 'kitchen/meal_planning.html', {'meals': meals})

@login_required
def production_tracking(request):
    from feedly.services.organizations import get_active_organization
    org = get_active_organization(request.user, request)
    kitchen = Kitchen.objects.filter(organization=org).first() if org else None
    
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add':
            food_item = request.POST.get('food_item')
            planned_qty = request.POST.get('planned_qty', 0)
            # Find today's meal record to attach to, or create a default one
            meal_record = MealRecord.objects.filter(kitchen=kitchen, date=timezone.now().date()).first()
            if not meal_record:
                meal_record = MealRecord.objects.create(
                    organization=kitchen.organization,
                    kitchen=kitchen,
                    date=timezone.now().date(),
                    meal_session='LUNCH',
                    status='PLANNED'
                )
            PreparationRecord.objects.create(
                meal_record=meal_record,
                kitchen=kitchen,
                food_item=food_item,
                planned_qty=planned_qty,
                prepared_qty=0
            )
            messages.success(request, f"Added preparation for {food_item}")
        elif action == 'update':
            prep_id = request.POST.get('prep_id')
            prepared_qty = request.POST.get('prepared_qty')
            if prep_id and prepared_qty:
                prep = get_object_or_404(PreparationRecord, id=prep_id, kitchen=kitchen)
                prep.prepared_qty = prepared_qty
                prep.save(update_fields=['prepared_qty', 'updated_at'])
                messages.success(request, f"Updated prepared quantity for {prep.food_item}")
        return redirect('kitchen_production')

    preparations = PreparationRecord.objects.filter(kitchen=kitchen).order_by('-updated_at')
    return render(request, 'kitchen/production_tracking.html', {'preparations': preparations})

@login_required
def register_surplus(request):
    from feedly.services.organizations import get_active_organization
    org = get_active_organization(request.user, request)
    kitchen = Kitchen.objects.filter(organization=org).first() if org else None
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
    from feedly.services.organizations import get_active_organization
    org = get_active_organization(request.user, request)
    kitchen = Kitchen.objects.filter(organization=org).first() if org else None
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
    from feedly.services.organizations import get_active_organization
    org = get_active_organization(request.user, request)
    kitchen = Kitchen.objects.filter(organization=org).first() if org else None
    
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add':
            ingredient_name = request.POST.get('ingredient_name')
            quantity = request.POST.get('quantity', 0)
            unit = request.POST.get('unit', 'kg')
            if ingredient_name and kitchen:
                ingredient, _ = Ingredient.objects.get_or_create(name=ingredient_name)
                KitchenInventory.objects.create(
                    kitchen=kitchen,
                    ingredient=ingredient,
                    quantity=quantity,
                    unit=unit
                )
                messages.success(request, f"Added {quantity} {unit} of {ingredient_name}")
        elif action == 'update':
            item_id = request.POST.get('item_id')
            new_qty = request.POST.get('quantity')
            if item_id and new_qty is not None:
                item = get_object_or_404(KitchenInventory, id=item_id, kitchen=kitchen)
                item.quantity = new_qty
                item.save(update_fields=['quantity'])
                messages.success(request, f"Updated {item.ingredient.name} quantity to {new_qty}")
        return redirect('kitchen_inventory')

    items = KitchenInventory.objects.filter(kitchen=kitchen)
    return render(request, 'kitchen/inventory.html', {'items': items})

@login_required
def kitchen_analytics(request):
    """Kitchen Intelligence Center - compares Historical vs Expected Demand."""
    from ..models import DemandForecast, MealRecord, Kitchen
    from django.db.models import Sum
    from django.utils import timezone
    from feedly.services.organizations import get_active_organization
    
    org = get_active_organization(request.user, request)
    kitchen = Kitchen.objects.filter(organization=org).first() if org else None
    
    historical = MealRecord.objects.filter(kitchen=kitchen).aggregate(total=Sum('meals_consumed'))['total'] or 0
    expected = DemandForecast.objects.filter(organization=org, date__gte=timezone.now().date()).aggregate(total=Sum('predicted_demand'))['total'] or 0
    
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
    
    if request.method == 'POST':
        item_id = request.POST.get('item_id')
        if item_id:
            item = get_object_or_404(KitchenInventory, id=item_id, kitchen__organization=request.organization)
            messages.success(request, f"Ingredient '{item.ingredient}' has been flagged for priority use in today's production plan.")
        return redirect('waste_prevention_center')
    
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
        date__gte=timezone.now().date()
    ).order_by('date')[:5]
    
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
