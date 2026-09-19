from functools import wraps
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from ..models import UserProfile, OrganizationMember, SystemEvent
from ..decorators import get_organization_sector

User = get_user_model()

def smart_login_view(request):
    """Phase 44: Unified Smart Login Experience with Onboarding & Priority Routing."""
    if request.user.is_authenticated:
        return redirect('dashboard')
        
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        
        # Simple rate limiting using session
        attempts = request.session.get('login_attempts', 0)
        if attempts >= 5:
            messages.error(request, 'Too many failed attempts. Please try again later.')
            return render(request, 'auth/login.html')
            
        if not username or not password:
            messages.error(request, 'Please enter your email/username and password.')
        else:
            user = authenticate(request, username=username, password=password)
            
            # If not found, try by email if standard backend doesn't support it
            if not user and '@' in username:
                try:
                    user_obj = User.objects.get(email=username)
                    user = authenticate(request, username=user_obj.username, password=password)
                except User.DoesNotExist:
                    pass

            if user:
                # Phase 44: Account Status Check
                if hasattr(user, 'profile'):
                    if user.profile.account_status in ['SUSPENDED', 'DISABLED']:
                        messages.error(request, "Your account has been suspended or disabled. Please contact support.")
                        return redirect('login')
                
                login(request, user)
                request.session['login_attempts'] = 0
                
                # Set active org id
                active_org_id = request.session.get('active_organization_id')
                membership = None
                if not active_org_id:
                    membership = OrganizationMember.objects.filter(user=user, is_active=True).select_related('organization').first()
                    if membership:
                        request.session['active_organization_id'] = membership.organization.id
                        SystemEvent.objects.create(organization=membership.organization, event_type="INFO", description=f"User {user.username} logged in.")
                
                # Phase 45: Super Admin Auto-Provisioning & Onboarding Bypass
                if getattr(user, 'is_superuser', False):
                    # Ensure they have a SUPER_ADMIN profile
                    if not hasattr(user, 'profile'):
                        from feedly.models import UserProfile
                        UserProfile.objects.create(
                            user=user, 
                            role='SUPER_ADMIN',
                            account_status='ACTIVE',
                            onboarding_completed=True,
                            onboarding_step=3
                        )
                    elif not user.profile.onboarding_completed or user.profile.role != 'SUPER_ADMIN':
                        user.profile.role = 'SUPER_ADMIN'
                        user.profile.onboarding_completed = True
                        user.profile.account_status = 'ACTIVE'
                        user.profile.save()
                else:
                    # Phase 44: Onboarding Check for normal users
                    if hasattr(user, 'profile') and not user.profile.onboarding_completed:
                        return redirect('onboarding_start')
                
                # Phase 44: Resolve Workspace Priority
                from feedly.services.permissions import get_permitted_workspaces, get_default_workspace
                permitted = get_permitted_workspaces(user)
                
                last_workspace = request.session.get('active_workspace')
                preferred_workspace = user.profile.preferred_workspace if hasattr(user, 'profile') else None
                default_workspace = get_default_workspace(user)
                
                target_workspace = None
                if last_workspace and last_workspace in permitted:
                    target_workspace = last_workspace
                elif preferred_workspace and preferred_workspace in permitted:
                    target_workspace = preferred_workspace
                elif default_workspace and default_workspace in permitted:
                    target_workspace = default_workspace
                elif permitted:
                    target_workspace = list(permitted)[0]
                
                if target_workspace:
                    request.session['active_workspace'] = target_workspace
                
                next_url = request.GET.get('next')
                if next_url:
                    return redirect(next_url)
                return redirect('dashboard')
            else:
                request.session['login_attempts'] = attempts + 1
                messages.error(request, "We couldn't sign you in. Check your credentials and try again.")
                
    return render(request, 'auth/login.html')

def role_selection_view(request):
    """Phase 42: Redirect old role selection to new smart login."""
    return redirect('login')

def role_login_view(request, role):
    """Phase 42: Redirect old role login to new smart login."""
    return redirect('login')

def login_view(request, persona=None):
    return redirect('login')

def register_view(request, role=None):
    """Phase 42: Unified progressive registration."""
    if request.user.is_authenticated:
        return redirect('dashboard')
        
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        selected_role = request.POST.get('role', role or 'FARMER').upper()
        
        if User.objects.filter(username=username).exists() or (email and User.objects.filter(email=email).exists()):
            messages.error(request, 'Account with this username or email already exists.')
        else:
            with transaction.atomic():
                user = User.objects.create_user(username=username, email=email, password=password)
                UserProfile.objects.create(user=user, role=selected_role)
                login(request, user)
                
                # No org assigned yet upon register, so we can't create SystemEvent
                return redirect('dashboard')
                
    return render(request, 'auth/register.html', {'role': role})

@login_required
def logout_view(request):
    username = request.user.username
    logout(request)
    org_member = request.user.organization_memberships.filter(is_active=True).first()
    if org_member:
        SystemEvent.objects.create(
            organization=org_member.organization,
            event_type="INFO",
            description=f"User {username} logged out."
        )
    messages.success(request, 'You have been securely logged out.')
    return redirect('login')

@login_required
def switch_workspace(request, workspace):
    """Phase 44: Allow users to switch their active workspace if authorized."""
    from feedly.services.permissions import get_permitted_workspaces
    
    permitted = get_permitted_workspaces(request.user)
    
    if workspace in permitted:
        request.session['active_workspace'] = workspace
        messages.success(request, f"Switched to {workspace} workspace.")
        if workspace == 'AGRICULTURE':
            return redirect('workspace_agri_dashboard')
        elif workspace == 'KITCHEN':
            return redirect('workspace_kitchen_dashboard')
        elif workspace == 'REDISTRIBUTION':
            return redirect('workspace_redistribution_dashboard')
        elif workspace == 'LOGISTICS':
            return redirect('workspace_logistics_dashboard')
        elif workspace == 'ADMIN':
            return redirect('workspace_admin_dashboard')
    else:
        from django.shortcuts import render
        return render(request, 'errors/403.html', {
            'required_workspace': workspace,
            'message': f"Permission denied to access the {workspace} workspace."
        }, status=403)
