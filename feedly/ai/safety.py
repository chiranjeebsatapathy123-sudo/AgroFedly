from feedly.models import OrganizationMember
import logging

logger = logging.getLogger(__name__)

class AISafetyGuard:
    """
    Validates AI-driven actions to ensure they are transaction-safe, authorized, and non-destructive.
    """
    
    @staticmethod
    def validate_action(action_type, user, organization, target_object=None, **kwargs):
        """
        Validates if a user is allowed to perform a specific AI-assisted action on a target object.
        Returns (True, "") if safe, (False, "reason") if blocked.
        """
        if not user or not user.is_authenticated:
            return False, "User is not authenticated."
            
        try:
            membership = OrganizationMember.objects.get(user=user, organization=organization, is_active=True)
        except OrganizationMember.DoesNotExist:
            return False, "User does not belong to this organization."

        # Owner and Admin can do anything
        if membership.role in ["OWNER", "ADMIN"]:
            pass
        elif membership.role == "VIEWER":
            return False, "Viewers cannot execute AI actions."
        else:
            # Domain-specific constraints for MANAGER/STAFF
            if action_type == "DELETE_RECORD":
                return False, f"Role {membership.role} is not permitted to delete records."

        # Domain specific validation
        if action_type == "REDISTRIBUTE":
            quantity = kwargs.get('quantity', 0)
            if target_object and hasattr(target_object, 'quantity'):
                if quantity > target_object.quantity:
                    return False, f"The requested redistribution ({quantity}) exceeds available surplus ({target_object.quantity})."
            
        if action_type == "APPROVE_SAFETY":
            if membership.role not in ["OWNER", "ADMIN", "MANAGER"]:
                return False, "Only managers or admins can approve food safety."

        return True, "Action is authorized and safe."
