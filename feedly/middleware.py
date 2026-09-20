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
        
        # Bypass DB for health checks
        if request.path.startswith('/health/') or request.path.startswith('/liveness/') or request.path.startswith('/readiness/'):
            return
            
        if request.user.is_authenticated:
            # Phase 45: Vercel Ephemeral DB Hotfix
            # If the user exists in session but the profile was wiped (due to Vercel SQLite resetting),
            # auto-provision it here to prevent 'role_selection' redirect loops.
            if not hasattr(request.user, 'profile'):
                from feedly.models import UserProfile
                # Grant super admins the SUPER_ADMIN role so they can access all features
                role = 'SUPER_ADMIN' if getattr(request.user, 'is_superuser', False) else 'FARMER'
                UserProfile.objects.create(
                    user=request.user, 
                    role=role,
                    account_status='ACTIVE',
                    onboarding_completed=True,
                    onboarding_step=3
                )
                
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

import traceback
from django.shortcuts import render
from .models import AppError

class AppErrorMiddleware(MiddlewareMixin):
    """
    Catches 500 exceptions, logs them to AppError model, and displays a user-friendly error page.
    """
    def process_exception(self, request, exception):
        # Ignore 404s and common handled errors if needed
        
        tb_str = traceback.format_exc()
        
        # Check if identical error exists recently
        error_type = type(exception).__name__
        path = request.path
        
        # Try to increment existing unresolved error
        existing_error = AppError.objects.filter(
            error_type=error_type,
            path=path,
            status='NEW'
        ).first()
        
        if existing_error:
            existing_error.occurrence_count += 1
            existing_error.save(update_fields=['occurrence_count'])
        else:
            AppError.objects.create(
                error_type=error_type,
                message=str(exception),
                traceback=tb_str,
                path=path,
                user=request.user if request.user.is_authenticated else None,
                organization=getattr(request, 'organization', None),
                severity='HIGH'
            )
            
        # Return generic error page (500)
        return render(request, 'errors/500_generic.html', status=500)
