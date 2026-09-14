from django.conf import settings
from ..models import FoodLedger

# Configurable safety thresholds
# These could potentially be loaded from DB settings in the future.
MAX_SAFE_TEMP = getattr(settings, 'FOOD_SAFETY_MAX_SAFE_TEMP', 5.0)
MAX_SAFE_HOURS = getattr(settings, 'FOOD_SAFETY_MAX_SAFE_HOURS', 24.0)

MAX_WARNING_TEMP = getattr(settings, 'FOOD_SAFETY_MAX_WARNING_TEMP', 8.0)
MAX_WARNING_HOURS = getattr(settings, 'FOOD_SAFETY_MAX_WARNING_HOURS', 36.0)


def evaluate_food_safety(food_instance, user=None):
    """
    Evaluates the safety of a SurplusFood instance based on configurable thresholds.
    Creates an audit trail in FoodLedger.
    NOTE: This is a basic heuristics check and does NOT constitute official certification.
    """
    is_safe = False
    status = "PENDING"
    alert = ""
    
    if food_instance.storage_temperature <= MAX_SAFE_TEMP and food_instance.storage_time_hours <= MAX_SAFE_HOURS:
        is_safe = True
        status = "SAFE"
        alert = "Safe for redistribution. (Basic temperature/time heuristic)"
    elif food_instance.storage_temperature <= MAX_WARNING_TEMP and food_instance.storage_time_hours <= MAX_WARNING_HOURS:
        is_safe = False
        status = "WARNING"
        alert = "Marginal conditions. Rapid redistribution or manual check required."
    else:
        is_safe = False
        status = "UNSAFE"
        reasons = []
        if food_instance.storage_temperature > MAX_WARNING_TEMP:
            reasons.append("temperature too high")
        if food_instance.storage_time_hours > MAX_WARNING_HOURS:
            reasons.append("storage time exceeded")
        alert = "Unsafe: " + " and ".join(reasons) + "."
        
    # Update instance
    food_instance.is_safe = is_safe
    food_instance.status = status
    food_instance.safety_alert = alert
    food_instance.save(update_fields=["is_safe", "status", "safety_alert"])
    
    # Create audit trail
    FoodLedger.objects.create(
        surplus_food=food_instance,
        action_type='QUALITY_CHECK' if is_safe else 'SPOILED',
        quantity=food_instance.quantity,
        performed_by=user,
        notes=f"Safety evaluation run. Status: {status}. {alert}"
    )
    
    return is_safe, status, alert
