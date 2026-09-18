from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q
from django.utils import timezone
from ..models import (
    Organization, OrganizationMember, CustomRole, 
    ApprovalWorkflow, ApprovalRequest, ApprovalActionLog,
    UserTask, SmartAlert, SystemEvent, TenantAuditLog, APIKey, Webhook
)
from ..decorators import _organization_required, require_role

@login_required
@_organization_required
@require_role(['OWNER', 'ADMIN'])
def custom_roles_list(request):
    roles = request.organization.custom_roles.all()
    return render(request, 'enterprise/custom_roles.html', {'roles': roles})

@login_required
@_organization_required
def approval_inbox(request):
    """Inbox for users to see approvals assigned to them or their roles."""
    org = request.organization
    member = request.membership

    # Find approvals where status is PENDING and this user can approve it
    # This involves checking if the workflow step matches their role or specific user
    pending_approvals = ApprovalRequest.objects.filter(
        workflow__organization=org,
        status='PENDING'
    ).select_related('workflow', 'requester').order_by('-created_at')

    # In a real implementation, we would filter by the current step and the user's roles
    # For now, we display all pending for the org to the user if they have access
    
    return render(request, 'enterprise/approval_inbox.html', {
        'pending_approvals': pending_approvals
    })

@login_required
@_organization_required
def operations_queue(request):
    """Central operations queue showing Tasks, Alerts, and Events requiring attention."""
    org = request.organization
    
    # 1. Open User Tasks
    tasks = UserTask.objects.filter(organization=org, status__in=['OPEN', 'IN_PROGRESS']).order_by('due_date')
    
    # 2. Unresolved Smart Alerts
    alerts = SmartAlert.objects.filter(organization=org, is_resolved=False).order_by('-created_at')
    
    # 3. Critical System Events (Anomalies)
    anomalies = SystemEvent.objects.filter(organization=org, severity='CRITICAL').order_by('-timestamp')[:10]

    return render(request, 'enterprise/operations_queue.html', {
        'tasks': tasks,
        'alerts': alerts,
        'anomalies': anomalies
    })

@login_required
@_organization_required
@require_role(['OWNER', 'ADMIN'])
def security_center(request):
    """Security dashboard showing audit logs, API usage, and permissions."""
    org = request.organization
    
    audit_logs = TenantAuditLog.objects.filter(organization=org).order_by('-timestamp')[:50]
    api_keys = APIKey.objects.filter(organization=org)
    webhooks = Webhook.objects.filter(organization=org)
    
    return render(request, 'enterprise/security_center.html', {
        'audit_logs': audit_logs,
        'api_keys': api_keys,
        'webhooks': webhooks
    })

@login_required
@_organization_required
def my_work(request):
    """Personal productivity dashboard."""
    org = request.organization
    
    my_tasks = UserTask.objects.filter(organization=org, assigned_to=request.user, status__in=['OPEN', 'IN_PROGRESS']).order_by('due_date')
    my_approvals = ApprovalRequest.objects.filter(workflow__organization=org, status='PENDING') # Simplified for now
    
    return render(request, 'enterprise/my_work.html', {
        'my_tasks': my_tasks,
        'my_approvals': my_approvals
    })

@login_required
@_organization_required
@require_role(['OWNER', 'ADMIN'])
def system_health(request):
    """System Health and AI Readiness Dashboard."""
    org = request.organization
    return render(request, 'enterprise/system_health.html', {
        'org': org
    })

@login_required
@_organization_required
@require_role(['OWNER', 'ADMIN'])
def data_quality(request):
    """Data Quality Center for AI Predictions."""
    org = request.organization
    
    # Mock issues for demo purposes
    issues = [
        {'title': 'Missing Coordinates', 'count': 3, 'severity': 'critical', 'desc': 'Farms missing GPS boundaries affecting weather forecasting.'},
        {'title': 'Stale Soil Data', 'count': 12, 'severity': 'warning', 'desc': 'Fields without soil tests in the last 6 months.'},
        {'title': 'Incomplete Deliveries', 'count': 0, 'severity': 'info', 'desc': 'Deliveries missing proof of delivery signatures.'},
        {'title': 'Unmapped Produce', 'count': 2, 'severity': 'warning', 'desc': 'Produce batches without associated fields or harvest logs.'},
    ]
    
    return render(request, 'enterprise/data_quality.html', {
        'org': org,
        'issues': issues
    })
