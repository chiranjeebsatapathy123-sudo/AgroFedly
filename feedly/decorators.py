from functools import wraps
from django.contrib import messages
from django.shortcuts import redirect
from .views import _organization_required

def require_org_role(allowed_roles):
    """
    Decorator for views that checks that the user has a specific role
    within their active organization.
    Assumes @_organization_required has already populated request.membership.
    """
    def decorator(view_func):
        @wraps(view_func)
        @_organization_required
        def _wrapped_view(request, *args, **kwargs):
            if request.membership.role not in allowed_roles:
                messages.error(request, f"Permission denied. Required role: {', '.join(allowed_roles)}")
                return redirect("organization_dashboard")
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator
