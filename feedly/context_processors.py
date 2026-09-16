def organization_context(request):
    """
    Exposes the active organization and user's membership to templates globally.
    """
    if hasattr(request, 'organization') and request.organization:
        memberships = getattr(request.user, 'organization_memberships', None)
        available_memberships = []
        if memberships:
            available_memberships = memberships.filter(is_active=True).select_related('organization')
        
        return {
            'active_org': request.organization,
            'active_membership': getattr(request, 'org_membership', None),
            'available_memberships': available_memberships,
        }
    return {}
