from django.utils import timezone
from ..models import SurplusFood, Delivery, Recipient, AgriculturalProduce, MealRecord

class DataQualityEngine:
    def __init__(self, organization):
        self.org = organization
        self.issues = []

    def run_audit(self):
        """Runs a complete data quality audit for the organization."""
        self.issues = []
        self._check_surplus()
        self._check_deliveries()
        self._check_recipients()
        self._check_produce()
        
        status = "safe"
        if len(self.issues) > 0:
            status = "warning"
        if any(i['severity'] == 'CRITICAL' for i in self.issues):
            status = "critical"
            
        return {
            "status": status,
            "issue_count": len(self.issues),
            "issues": self.issues
        }
        
    def _add_issue(self, severity, category, message, related_object=None):
        self.issues.append({
            "severity": severity,
            "category": category,
            "message": message,
            "related_object": str(related_object) if related_object else None
        })

    def _check_surplus(self):
        # Negative or zero quantities
        invalid_qty = SurplusFood.objects.filter(organization=self.org, quantity__lte=0)
        for s in invalid_qty:
            self._add_issue("CRITICAL", "Surplus", f"Surplus record has invalid quantity ({s.quantity}).", s)
            
        # Stale pending records (> 48 hours)
        stale_threshold = timezone.now() - timezone.timedelta(hours=48)
        stale_surplus = SurplusFood.objects.filter(
            organization=self.org, 
            status="PENDING", 
            created_at__lt=stale_threshold
        )
        for s in stale_surplus:
            self._add_issue("WARNING", "Surplus", "Surplus record has been PENDING for over 48 hours.", s)

    def _check_deliveries(self):
        # Invalid state transitions (e.g., delivered but quantity is 0)
        invalid_qty = Delivery.objects.filter(sender=self.org, quantity__lte=0)
        for d in invalid_qty:
            self._add_issue("CRITICAL", "Delivery", f"Delivery record has invalid quantity ({d.quantity}).", d)
            
        # Stale in-transit deliveries
        stale_threshold = timezone.now() - timezone.timedelta(hours=24)
        stale_transit = Delivery.objects.filter(
            sender=self.org, 
            status="IN_TRANSIT", 
            updated_at__lt=stale_threshold
        )
        for d in stale_transit:
            self._add_issue("WARNING", "Delivery", "Delivery has been stuck IN_TRANSIT for over 24 hours.", d)

    def _check_recipients(self):
        # Recipients with missing capacity
        missing_capacity = Recipient.objects.filter(organization=self.org, capacity=0)
        for r in missing_capacity:
            self._add_issue("INFO", "Recipient", "Recipient is missing capacity information.", r)

    def _check_produce(self):
        invalid_qty = AgriculturalProduce.objects.filter(supplier=self.org, quantity__lt=0)
        for p in invalid_qty:
            self._add_issue("CRITICAL", "Produce", f"Produce record has negative quantity ({p.quantity}).", p)
