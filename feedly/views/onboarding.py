from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from feedly.models import UserProfile, Organization, OrganizationMember
from feedly.services.permissions import get_default_workspace, get_permitted_workspaces

@login_required
def onboarding_start(request):
    """Step 1: Complete User Profile."""
    user = request.user
    
    # If already completed, just send to dashboard
    if hasattr(user, 'profile') and user.profile.onboarding_completed:
        return redirect('dashboard')
        
    profile, created = UserProfile.objects.get_or_create(user=user)
    
    if request.method == 'POST':
        # Update user
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        user.first_name = first_name
        user.last_name = last_name
        user.save()
        
        # Update profile
        profile.phone = request.POST.get('phone', '').strip()
        profile.location = request.POST.get('location', '').strip()
        profile.timezone = request.POST.get('timezone', 'UTC')
        profile.preferred_language = request.POST.get('preferred_language', 'en')
        profile.onboarding_step = 2
        profile.save()
        
        return redirect('onboarding_org')
        
    context = {
        'profile': profile,
        'user': user
    }
    return render(request, 'onboarding/step1_profile.html', context)

@login_required
def onboarding_org(request):
    """Step 2: Organization setup."""
    user = request.user
    if not hasattr(user, 'profile') or user.profile.onboarding_completed:
        return redirect('dashboard')
        
    profile = user.profile
    if profile.onboarding_step < 2:
        return redirect('onboarding_start')
        
    if request.method == 'POST':
        org_action = request.POST.get('org_action')
        
        if org_action == 'CREATE':
            org_name = request.POST.get('org_name')
            org_type = request.POST.get('org_type')
            
            # Map role to org type if not provided
            if not org_type:
                if profile.role in if not (getattr(request.user, 'is_superuser', False) or getattr(request.user, 'profile', None) and getattr(request.user.profile, 'role', '') in ['SUPER_ADMIN', 'ADMIN']) and request.membership.role not in ['FARMER', 'FPO', 'AGRIBUSINESS']:
                    org_type = 'SUPPLIER'
                elif profile.role == 'NGO':
                    org_type = 'NGO'
                else:
                    org_type = 'COMPANY'
            
            org = Organization.objects.create(name=org_name, organization_type=org_type)
            OrganizationMember.objects.create(
                organization=org,
                user=user,
                role='OWNER',
                status='ACTIVE'
            )
            
            profile.onboarding_step = 3
            profile.save()
            return redirect('onboarding_role_setup')
            
        elif org_action == 'JOIN':
            # Implement join by code or request logic here later
            messages.info(request, "Join by code is coming soon. Please create an organization for now.")
            return redirect('onboarding_org')
            
    context = {
        'profile': profile
    }
    return render(request, 'onboarding/step2_org.html', context)

@login_required
def onboarding_role_setup(request):
    """Step 3: Role-specific setup (e.g., add farm)."""
    user = request.user
    if not hasattr(user, 'profile') or user.profile.onboarding_completed:
        return redirect('dashboard')
        
    profile = user.profile
    if profile.onboarding_step < 3:
        return redirect('onboarding_org')
        
    membership = OrganizationMember.objects.filter(user=user, is_active=True).first()
    org = membership.organization if membership else None
    
    if request.method == 'POST':
        # E.g., Farmer adding a Farm
        if profile.role in ['FARMER', 'FPO'] and org:
            farm_name = request.POST.get('farm_name', '').strip()
            if farm_name:
                from feedly.models import Farm
                Farm.objects.create(
                    organization=org,
                    owner=user,
                    name=farm_name
                )
                
        # Finish onboarding
        profile.onboarding_completed = True
        profile.account_status = 'ACTIVE'
        profile.save()
        
        if org:
            org.onboarding_completed = True
            org.save()
            
        messages.success(request, "Welcome to AgroFedly! Your account setup is complete.")
        return redirect('dashboard')
        
    context = {
        'profile': profile,
        'organization': org
    }
    return render(request, 'onboarding/step3_setup.html', context)
