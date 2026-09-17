from feedly.models import FarmField, AgriculturalProduce, StorageRecord, AIModelRegistry
from django.core.exceptions import ValidationError
from django.utils import timezone

class DataQualityEngine:
    """
    Validates data integrity and flags anomalies before AI inference or critical workflows.
    """
    
    @staticmethod
    def validate_farm_field(field_id):
        field = FarmField.objects.filter(id=field_id).first()
        if not field:
            return False, "Field not found"
        if field.area_hectares <= 0:
            return False, "Invalid field area (must be > 0)"
        return True, "Valid"
        
    @staticmethod
    def validate_produce_quantity(quantity):
        if quantity < 0:
            return False, "Quantity cannot be negative"
        if quantity > 1000000:
            return False, "Anomalously high quantity"
        return True, "Valid"
        
    @staticmethod
    def run_full_audit():
        """
        Background task to find corrupted records.
        """
        issues = []
        
        # Check for negative areas
        bad_fields = FarmField.objects.filter(area_hectares__lte=0)
        for f in bad_fields:
            issues.append(f"Field {f.id} has invalid area {f.area_hectares}")
            
        # Check AI Models
        models = AIModelRegistry.objects.all()
        if not models.exists():
            issues.append("No AI models registered in registry.")
            
        return issues
