from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from feedly.models import Kitchen, MealRecord, PreparationRecord, SurplusFood, KitchenInventory, KitchenAlert
from django.utils import timezone

@login_required
def kitchen_dashboard(request):
    kitchen = Kitchen.objects.filter(organization__members__user=request.user).first()
    if not kitchen:
        return render(request, 'kitchen/no_kitchen.html')
        
    today = timezone.now().date()
    meals_today = MealRecord.objects.filter(kitchen=kitchen, date=today)
    surplus_today = SurplusFood.objects.filter(kitchen=kitchen, created_at__date=today)
    alerts = KitchenAlert.objects.filter(kitchen=kitchen, is_resolved=False)
    
    context = {
        'kitchen': kitchen,
        'meals': meals_today,
        'surplus': surplus_today,
        'alerts': alerts
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
        # Simplified process
        SurplusFood.objects.create(
            kitchen=kitchen,
            organization=kitchen.organization,
            food_name=food_name,
            quantity=quantity,
            safety_status='PENDING_CHECK'
        )
        return redirect('kitchen_redistribution')
    return render(request, 'kitchen/register_surplus.html')

@login_required
def redistribution_queue(request):
    kitchen = Kitchen.objects.filter(organization__members__user=request.user).first()
    surplus = SurplusFood.objects.filter(kitchen=kitchen).order_by('-created_at')
    
    # Kanban columns
    columns = {
        'draft': surplus.filter(safety_status='PENDING_CHECK'),
        'safety': surplus.filter(safety_status='ELIGIBLE', status='PENDING'),
        'matched': surplus.filter(status='MATCHED'),
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
    kitchen = Kitchen.objects.filter(organization__members__user=request.user).first()
    return render(request, 'kitchen/analytics.html', {'kitchen': kitchen})
