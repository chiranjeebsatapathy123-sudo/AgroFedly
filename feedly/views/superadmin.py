from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from feedly.models import UserProfile, Organization, OrganizationMember, DemandForecast, Delivery, SystemEvent, AIModelRegistry
from django.contrib.auth import get_user_model
from django.db.models import Count
from django.utils import timezone
from datetime import timedelta

User = get_user_model()

@login_required
def platform_admin_dashboard(request):
    """
    Phase 45: True Platform Administration Dashboard for Super Admins.
    Displays global stats rather than org-specific stats.
    """
    if not getattr(request.user, 'is_superuser', False):
        # Fallback to org admin dashboard if they somehow bypassed router
        return redirect('workspace_admin_dashboard')
        
    request.session['active_workspace'] = 'ADMIN'
    
    # Platform-wide Metrics
    total_users = User.objects.count()
    total_orgs = Organization.objects.filter(is_active=True).count()
    total_deliveries = Delivery.objects.count()
    
    # Active Users (Logged in last 30 days)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    active_users = User.objects.filter(last_login__gte=thirty_days_ago).count()
    
    # System Health (Basic mock or actual if you have a health model)
    system_health = "OPTIMAL"
    
    # Recent Audit Logs across the platform
    recent_events = SystemEvent.objects.all().order_by('-timestamp')[:10]
    
    # Active AI Models
    active_models = AIModelRegistry.objects.filter(status='ACTIVE').count()
    
    # Organizations Breakdown
    orgs_breakdown = Organization.objects.values('organization_type').annotate(count=Count('id'))
    
    context = {
        'total_users': total_users,
        'active_users': active_users,
        'total_orgs': total_orgs,
        'total_deliveries': total_deliveries,
        'system_health': system_health,
        'recent_events': recent_events,
        'active_models': active_models,
        'orgs_breakdown': orgs_breakdown,
    }
    
    return render(request, 'admin/platform_admin_dashboard.html', context)

@login_required
def workspace_admin_router(request):
    """
    Phase 45: Routes users to the appropriate admin dashboard based on superuser status.
    """
    if getattr(request.user, 'is_superuser', False):
        return platform_admin_dashboard(request)
    else:
        from feedly.views.organization import organization_admin_dashboard
        return organization_admin_dashboard(request)
