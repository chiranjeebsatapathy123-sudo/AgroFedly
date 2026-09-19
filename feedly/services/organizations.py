from feedly.models import OrganizationMember, Organization

def get_active_organization(user, request=None):
    """
    Canonical Organization Resolver.
    Resolves the user's current organization using the project's existing membership architecture.
    Handles:
    - no organization
    - inactive membership
    - suspended membership
    - multiple organizations
    - active organization
    - organization switching
    """
    if not user or not user.is_authenticated:
        return None

    # If the request already has an active organization in session (for users in multiple orgs)
    if request and 'active_organization_id' in request.session:
        org_id = request.session['active_organization_id']
        active_membership = OrganizationMember.objects.filter(
            user=user, 
            organization_id=org_id, 
            is_active=True
        ).exclude(status__in=['REMOVED', 'SUSPENDED']).first()
        
        if active_membership:
            if request:
                request.org_membership = active_membership
            return active_membership.organization

    # Fallback to the first active organization membership
    active_membership = OrganizationMember.objects.filter(
        user=user, 
        is_active=True
    ).exclude(status__in=['REMOVED', 'SUSPENDED']).select_related('organization').first()

    if active_membership:
        if request:
            request.session['active_organization_id'] = active_membership.organization.id
            request.org_membership = active_membership
        return active_membership.organization

    # If no membership is found, check if they are directly attached to an org (legacy fallback)
    if hasattr(user, 'organization') and user.organization:
        # We don't have a valid active membership record, but there is a legacy attachment.
        # It's better to rely on OrganizationMember, but for backwards compatibility:
        return user.organization

    return None
