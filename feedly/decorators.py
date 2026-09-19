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


# ----------------- AGROFEDLY 2.0 RBAC -----------------

def require_profile_role(roles):
    """
    Decorator to ensure the user has a UserProfile and their role is in the allowed `roles` list.
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped_view(request, *args, **kwargs):
            if hasattr(request.user, 'profile'):
                status = request.user.profile.account_status
                if status in ['SUSPENDED', 'DISABLED']:
                    messages.error(request, "Your account has been suspended or disabled.")
                    from django.contrib.auth import logout
                    logout(request)
                    return redirect('login')
                if status == 'INVITED':
                    messages.warning(request, "Please complete your registration first.")
                    return redirect('onboarding_start')
            
            if not hasattr(request.user, 'profile'):
                messages.error(request, "Please complete your profile registration first.")
                return redirect("role_selection")
            
            if request.user.profile.role not in roles:
                messages.error(request, f"Permission denied. Required role: {', '.join(roles)}")
                return redirect("dashboard")
                
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

# Convenience decorators
require_farmer = require_profile_role(['FARMER'])
require_fpo = require_profile_role(['FPO'])
require_agribusiness = require_profile_role(['AGRIBUSINESS'])
require_officer = require_profile_role(['OFFICER'])
require_ngo = require_profile_role(['NGO'])
require_researcher = require_profile_role(['RESEARCHER'])
require_admin = require_profile_role(['ADMIN'])

# ----------------- PHASE 42: SECTOR & WORKSPACE RBAC -----------------

def get_organization_sector(organization):
    if not organization:
        return None
    org_type = organization.organization_type
    if org_type == 'SUPPLIER':
        return 'AGRICULTURE'
    elif org_type == 'NGO':
        return 'REDISTRIBUTION'
    elif org_type in ['COMPANY', 'HOSPITAL', 'SCHOOL', 'COLLEGE', 'INSTITUTION']:
        return 'KITCHEN'
    return 'UNKNOWN'

def require_sector(sector):
    """
    Decorator to ensure the user's evaluated permissions allow access to this workspace/sector.
    Sectors: AGRICULTURE, KITCHEN, REDISTRIBUTION, LOGISTICS, ADMIN
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped_view(request, *args, **kwargs):
            if hasattr(request.user, 'profile'):
                status = request.user.profile.account_status
                if status in ['SUSPENDED', 'DISABLED']:
                    from django.shortcuts import render
                    return render(request, 'errors/403.html', {
                        'required_workspace': sector,
                        'message': "Permission denied. Your account is suspended or disabled."
                    }, status=403)
                    
            from feedly.services.permissions import get_permitted_workspaces
            permitted_workspaces = get_permitted_workspaces(request.user)
            
            if sector not in permitted_workspaces:
                from django.shortcuts import render
                return render(request, 'errors/403.html', {
                    'required_workspace': sector,
                    'message': f"Permission denied. This view requires {sector} sector authorization."
                }, status=403)
                
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

def require_workspace(workspace):
    """
    Decorator to ensure the user's active session workspace matches the required workspace.
    AND they are actually allowed to access it.
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped_view(request, *args, **kwargs):
            if hasattr(request.user, 'profile'):
                status = request.user.profile.account_status
                if status in ['SUSPENDED', 'DISABLED']:
                    from django.shortcuts import render
                    return render(request, 'errors/403.html', {
                        'required_workspace': workspace,
                        'message': "Permission denied. Your account is suspended or disabled."
                    }, status=403)
                    
            from feedly.services.permissions import get_permitted_workspaces
            permitted_workspaces = get_permitted_workspaces(request.user)
            
            if workspace not in permitted_workspaces:
                from django.shortcuts import render
                return render(request, 'errors/403.html', {
                    'required_workspace': workspace,
                    'message': f"Permission denied. Switch to the {workspace} workspace first."
                }, status=403)
                
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator
