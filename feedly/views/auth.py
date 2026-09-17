from functools import wraps
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from ..models import UserProfile

User = get_user_model()

def role_selection_view(request):
    """Phase 2: Initial screen where users choose their role."""
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'role_selection.html')

def role_login_view(request, role):
    """Phase 4: Role-specific login form."""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    role = role.upper()
    valid_roles = dict(UserProfile.ROLE_CHOICES).keys()
    if role not in valid_roles:
        messages.error(request, "Invalid role selected.")
        return redirect('role_selection')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        
        if not username or not password:
            messages.error(request, 'Enter credentials.')
        else:
            user = authenticate(request, username=username, password=password)
            if user:
                if hasattr(user, 'profile') and user.profile.role == role:
                    login(request, user)
                    return redirect(request.GET.get('next') or 'dashboard')
                else:
                    messages.error(request, f'This account is not registered as a {role}.')
            else:
                messages.error(request, 'Invalid credentials.')
                
    return render(request, 'role_login.html', {'role': role})

def register_view(request, role):
    """Phase 5: Role-specific progressive registration."""
    if request.user.is_authenticated:
        return redirect('dashboard')
        
    role = role.upper()
    valid_roles = dict(UserProfile.ROLE_CHOICES).keys()
    if role not in valid_roles:
        return redirect('role_selection')
        
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
        else:
            with transaction.atomic():
                user = User.objects.create_user(username=username, email=email, password=password)
                UserProfile.objects.create(user=user, role=role)
                login(request, user)
                return redirect('dashboard')
                
    return render(request, 'role_register.html', {'role': role})

def login_view(request, persona=None):
    return redirect('role_selection')

@login_required
def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('role_selection')
