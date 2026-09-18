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
    """Phase 42: Unified Smart Login Experience."""
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
            # Allow login by email or username (custom authenticate backend or simple check)
            # Default authenticate usually takes username. Let's try username.
            user = authenticate(request, username=username, password=password)
            
            # If not found, try by email if standard backend doesn't support it
            if not user and '@' in username:
                try:
                    user_obj = User.objects.get(email=username)
                    user = authenticate(request, username=user_obj.username, password=password)
                except User.DoesNotExist:
                    pass

            if user:
                login(request, user)
                request.session['login_attempts'] = 0
                
                # Resolve workspace
                active_org_id = request.session.get('active_organization_id')
                if not active_org_id:
                    # Find highest priority active membership
                    membership = OrganizationMember.objects.filter(
                        user=user, 
                        is_active=True
                    ).select_related('organization').first()
                    
                    if membership:
                        request.session['active_organization_id'] = membership.organization.id
                        request.session['active_workspace'] = get_organization_sector(membership.organization)
                    elif hasattr(user, 'profile'):
                        # Fallback to legacy profile role
                        role = user.profile.role
                        if role == 'FARMER' or role == 'FPO':
                            request.session['active_workspace'] = 'AGRICULTURE'
                        elif role == 'NGO':
                            request.session['active_workspace'] = 'REDISTRIBUTION'
                        elif role == 'ADMIN':
                            request.session['active_workspace'] = 'ADMIN'
                        else:
                            request.session['active_workspace'] = 'KITCHEN'

                # Audit Log
                SystemEvent.objects.create(
                    event_type="INFO",
                    message=f"User {user.username} logged in securely.",
                    source="Auth"
                )
                
                next_url = request.GET.get('next')
                if next_url:
                    return redirect(next_url)
                return redirect('dashboard')
            else:
                request.session['login_attempts'] = attempts + 1
                messages.error(request, "We couldn't sign you in. Check your credentials and try again.")
                # Audit Log for failure
                SystemEvent.objects.create(
                    event_type="WARNING",
                    message=f"Failed login attempt for {username}",
                    source="Auth"
                )
                
    return render(request, 'auth/login.html')

def role_selection_view(request):
    """Phase 42: Redirect old role selection to new smart login."""
    return redirect('smart_login')

def role_login_view(request, role):
    """Phase 42: Redirect old role login to new smart login."""
    return redirect('smart_login')

def login_view(request, persona=None):
    return redirect('smart_login')

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
                
                SystemEvent.objects.create(
                    event_type="INFO",
                    message=f"New user registered: {user.username}",
                    source="Auth"
                )
                return redirect('dashboard')
                
    return render(request, 'auth/register.html', {'role': role})

@login_required
def logout_view(request):
    username = request.user.username
    logout(request)
    SystemEvent.objects.create(
        event_type="INFO",
        message=f"User {username} logged out.",
        source="Auth"
    )
    messages.success(request, 'You have been securely logged out.')
    return redirect('smart_login')

@login_required
def switch_workspace(request, workspace):
    """Phase 42: Allow users to switch their active workspace if authorized."""
    # Here we would normally validate if they actually have permissions for this workspace.
    # For now, if they are an admin or have a membership in that sector, allow it.
    
    # In a full implementation, we'd query OrganizationMember to see if they have an org in this sector
    user = request.user
    is_admin = hasattr(user, 'profile') and user.profile.role == 'ADMIN'
    
    authorized = is_admin
    
    if not authorized:
        for membership in OrganizationMember.objects.filter(user=user, is_active=True).select_related('organization'):
            if get_organization_sector(membership.organization) == workspace:
                authorized = True
                request.session['active_organization_id'] = membership.organization.id
                break
                
    # Fallback to Profile role
    if not authorized and hasattr(user, 'profile'):
        profile_workspace = 'KITCHEN'
        role = user.profile.role
        if role in ['FARMER', 'FPO']: profile_workspace = 'AGRICULTURE'
        elif role == 'NGO': profile_workspace = 'REDISTRIBUTION'
        
        if profile_workspace == workspace:
            authorized = True
            
    if authorized:
        request.session['active_workspace'] = workspace
        messages.success(request, f"Switched to {workspace} workspace.")
    else:
        messages.error(request, f"You are not authorized to access the {workspace} workspace.")
        
    return redirect('dashboard')
