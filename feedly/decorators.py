from functools import wraps
from django.contrib import messages
from django.shortcuts import redirect
from .models import OrganizationMember
from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages

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








from django.contrib.auth.decorators import login_required
def _membership(request):
    memberships = OrganizationMember.objects.select_related('organization').filter(user=request.user, is_active=True, organization__is_active=True)
    active_id = request.session.get('active_organization_id')
    if active_id:
        active = memberships.filter(organization_id=active_id).first()
        if active:
            return active
    return memberships.order_by('-joined_at').first()

def _organization_required(view):

    @wraps(view)
    @login_required
    def wrapped(request, *args, **kwargs):
        membership = _membership(request)
        if not membership:
            messages.info(request, 'Register or join an organization to use this workspace.')
            return redirect('organization_register')
        request.membership = membership
        request.organization = membership.organization
        return view(request, *args, **kwargs)
    return wrapped

def _manager_required(view):

    @wraps(view)
    @_organization_required
    def wrapped(request, *args, **kwargs):
        if request.membership.role not in {'OWNER', 'ADMIN', 'MANAGER'}:
            messages.error(request, 'Manager permission is required for this action.')
            return redirect('organization_dashboard')
        return view(request, *args, **kwargs)
    return wrapped

