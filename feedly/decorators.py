from functools import wraps
from django.contrib import messages
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required

def require_organization(view_func):
    """
    Ensures the user has an active organization in their context via OrganizationMiddleware.
    """
    @wraps(view_func)
    @login_required
    def wrapped(request, *args, **kwargs):
        if not hasattr(request, 'organization') or not request.organization:
            messages.info(request, 'Register or join an organization to use this workspace.')
            return redirect('organization_onboarding')
            
        # Backward compatibility for old views relying on request.membership
        request.membership = request.org_membership
        return view_func(request, *args, **kwargs)
    return wrapped

def require_role(roles):
    """
    Decorator to ensure the user's active membership role is in the allowed `roles` list.
    """
    def decorator(view_func):
        @wraps(view_func)
        @require_organization
        def _wrapped_view(request, *args, **kwargs):
            if request.org_membership.role not in roles:
                messages.error(request, f"Permission denied. Required role: {', '.join(roles)}")
                return redirect("dashboard")
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

# Backwards compatibility names
_organization_required = require_organization

def _manager_required(view_func):
    return require_role(['OWNER', 'ADMIN', 'MANAGER'])(view_func)

require_org_role = require_role
