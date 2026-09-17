from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from feedly.models import UserProfile, OrganizationMember

@login_required
def user_profile(request):
    try:
        profile = request.user.userprofile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=request.user)
        
    memberships = OrganizationMember.objects.filter(user=request.user)
    
    if request.method == 'POST':
        # Update logic here if needed
        messages.success(request, 'Profile updated successfully.')
        return redirect('user_profile')
        
    context = {
        'profile': profile,
        'memberships': memberships,
    }
    return render(request, 'user_profile.html', context)

@login_required
def security_center(request):
    return render(request, 'security_center.html')
