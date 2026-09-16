from django.utils.deprecation import MiddlewareMixin
from .models import OrganizationMember, Organization

class OrganizationMiddleware(MiddlewareMixin):
    """
    Attaches the active organization and membership role to the request.
    This ensures that multi-tenant data is completely isolated.
    """
    def process_request(self, request):
        request.organization = None
        request.org_membership = None
        
        if request.user.is_authenticated:
            # Check session for selected org, otherwise use first active membership
            org_id = request.session.get('active_organization_id')
            
            if org_id:
                membership = OrganizationMember.objects.filter(
                    user=request.user, 
                    organization_id=org_id, 
                    is_active=True
                ).select_related('organization').first()
            else:
                membership = OrganizationMember.objects.filter(
                    user=request.user, 
                    is_active=True
                ).select_related('organization').first()
                
            if membership:
                request.organization = membership.organization
                request.org_membership = membership
                # Ensure session matches
                request.session['active_organization_id'] = membership.organization.id
