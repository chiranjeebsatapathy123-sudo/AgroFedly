from django.utils import timezone
from ..models import SurplusFood, Delivery, Recipient
from django.db.models import Sum

class SurplusCalculator:
    """
    Authoritative service for surplus calculation and priority scoring.
    """
    def __init__(self, organization):
        self.org = organization

    def get_total_surplus_quantity(self):
        """Authoritative source for total available surplus quantity."""
        # Only active, non-redistributed surplus counts towards total available
        surplus = SurplusFood.objects.filter(
            organization=self.org, 
            status__in=['PENDING', 'SAFE', 'WARNING']
        ).aggregate(total=Sum('quantity'))['total'] or 0
        return surplus

    def get_safe_surplus_quantity(self):
        """Authoritative source for safely redistributable surplus quantity."""
        surplus = SurplusFood.objects.filter(
            organization=self.org, 
            status='SAFE'
        ).aggregate(total=Sum('quantity'))['total'] or 0
        return surplus

    def get_unallocated_surplus(self):
        """Returns surplus items that have not yet been fully redistributed."""
        return SurplusFood.objects.filter(
            organization=self.org,
            status__in=['PENDING', 'SAFE', 'WARNING']
        ).order_by('-created_at')

    def calculate_priority_score(self, surplus_item):
        """
        Prioritizes surplus operationally based on documented factors:
        - Age / Time in storage
        - Storage Temperature
        - Quantity
        """
        score = 0
        
        # Factor 1: Age (Older = Higher priority to move before spoilage)
        age_hours = (timezone.now() - surplus_item.created_at).total_seconds() / 3600
        effective_age = max(age_hours, surplus_item.storage_time_hours)
        if effective_age > 24:
            score += 40
        elif effective_age > 12:
            score += 20
            
        # Factor 2: Temperature (Higher temp = higher risk of spoilage)
        if surplus_item.storage_temperature > 8.0:
            score += 30
        elif surplus_item.storage_temperature > 5.0:
            score += 15
            
        # Factor 3: Quantity (Larger quantities need more logistical planning, high priority)
        if surplus_item.quantity >= 100:
            score += 20
        elif surplus_item.quantity >= 50:
            score += 10
            
        # Cap at 100
        return min(100, score)
