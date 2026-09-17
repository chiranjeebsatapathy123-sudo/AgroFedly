from django.db import transaction
from ..models import Recipient, Redistribution, Delivery

class RecipientMatchingEngine:
    def __init__(self, organization):
        self.org = organization

    def get_recommendations(self, surplus_food):
        """
        Calculates match scores for all verified recipients for a given surplus item.
        Respects organization boundaries and recipient capacity.
        """
        if surplus_food.status != 'SAFE':
            return []

        ranked = []
        recipients = Recipient.objects.filter(
            organization=self.org, 
            verified=True, 
            capacity__gt=0
        )
        
        for recipient in recipients:
            # Capacity Match (1.0 = perfect match, < 1.0 = partial fit, > 1.0 = recipient can take more than available)
            fit = min(surplus_food.quantity, recipient.capacity) / max(surplus_food.quantity, 1)
            
            # Distance Match (Closer is better)
            distance_score = 1 / (1 + max(recipient.distance_km, 0))
            
            # Urgency
            urgency_score = min(max(recipient.urgency_score, 0), 100) / 100
            
            # Weighted Score
            score = 0.5 * fit + 0.3 * urgency_score + 0.2 * distance_score
            
            reasons = []
            if fit >= 0.8:
                reasons.append('optimal capacity match')
            elif fit >= 0.5:
                reasons.append('acceptable capacity match')
            
            if urgency_score >= 0.7:
                reasons.append('high urgency')
                
            if recipient.distance_km <= 10:
                reasons.append('close proximity')
                
            if reasons:
                explanation = f"{round(score * 100)}% match due to " + ', '.join(reasons) + "."
            else:
                explanation = f"{round(score * 100)}% match based on general suitability."

            ranked.append({
                'recipient': recipient,
                'score': round(score * 100, 1),
                'capacity': recipient.capacity,
                'distance_km': recipient.distance_km,
                'urgency': recipient.urgency_score,
                'explanation': explanation,
                'suggested_quantity': min(surplus_food.quantity, recipient.capacity)
            })

        ranked.sort(key=lambda x: x['score'], reverse=True)
        return ranked

    @transaction.atomic
    def allocate_surplus(self, surplus_food, recipient, requested_quantity, user=None):
        """
        Transaction-safe allocation of surplus.
        Enforces capacity and availability rules.
        """
        # Lock the rows for update to prevent concurrent allocation race conditions
        from ..models import SurplusFood
        surplus = SurplusFood.objects.select_for_update().get(id=surplus_food.id)
        locked_recipient = Recipient.objects.select_for_update().get(id=recipient.id)

        if surplus.organization != self.org or locked_recipient.organization != self.org:
            raise ValueError("Cross-organization allocation is not permitted.")
            
        if surplus.status != 'SAFE':
            raise ValueError("Only SAFE surplus can be redistributed.")

        allocation_qty = min(requested_quantity, surplus.quantity, locked_recipient.capacity)
        
        if allocation_qty <= 0:
            raise ValueError("Cannot allocate zero or negative quantity, or recipient is at full capacity.")

        # Create Redistribution Record
        redistribution = Redistribution.objects.create(
            organization=self.org,
            surplus=surplus,
            recipient=locked_recipient,
            quantity=allocation_qty
        )

        # Update Surplus
        surplus.quantity -= allocation_qty
        if surplus.quantity == 0:
            surplus.status = 'REDISTRIBUTED'
        surplus.save(update_fields=['quantity', 'status'])
        
        # Update Recipient Capacity
        locked_recipient.capacity -= allocation_qty
        locked_recipient.save(update_fields=['capacity'])

        # Create Delivery Request
        delivery = Delivery.objects.create(
            surplus=surplus,
            sender=self.org,
            receiver=self.org,
            status='REQUESTED',
            food_name=surplus.food_name,
            quantity=allocation_qty,
            pickup_address=self.org.address if self.org else "",
            delivery_address="Recipient: " + locked_recipient.name,
            created_by=user
        )

        # Log Traceability
        from ..models import ProduceTraceabilityLedger
        import uuid
        ProduceTraceabilityLedger.objects.create(
            transaction_id=str(uuid.uuid4()),
            transaction_type='ALLOCATED',
            surplus=surplus,
            quantity=allocation_qty,
            actor=user,
            organization=self.org,
            details=f"Allocated {allocation_qty} to {locked_recipient.name}. Delivery Tracking: {delivery.tracking_code}"
        )

        return redistribution, delivery
