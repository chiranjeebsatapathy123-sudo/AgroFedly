from feedly.models import UserProfile, OrganizationMember

WORKSPACES_META = {
    'AGRICULTURE': {'icon': 'fas fa-seedling', 'label': 'Agriculture', 'url_arg': 'AGRICULTURE'},
    'KITCHEN': {'icon': 'fas fa-utensils', 'label': 'Kitchen', 'url_arg': 'KITCHEN'},
    'REDISTRIBUTION': {'icon': 'fas fa-hands-helping', 'label': 'Redistribution', 'url_arg': 'REDISTRIBUTION'},
    'LOGISTICS': {'icon': 'fas fa-truck', 'label': 'Logistics', 'url_arg': 'LOGISTICS'},
    'ADMIN': {'icon': 'fas fa-cogs', 'label': 'Administration', 'url_arg': 'ADMIN'},
}

def get_permitted_workspaces(user):
    """
    Evaluates UserProfile, Organization properties, and OrganizationMember roles 
    to return a set of authorized workspace keys.
    """
    if not user.is_authenticated:
        return set()
        
    if getattr(user, 'is_superuser', False):
        return {'AGRICULTURE', 'KITCHEN', 'REDISTRIBUTION', 'LOGISTICS', 'ADMIN'}
        
    permitted = set()
    
    # Check Profile
    if hasattr(user, 'profile'):
        role = user.profile.role
        if role == 'SUPER_ADMIN':
            return {'AGRICULTURE', 'KITCHEN', 'REDISTRIBUTION', 'LOGISTICS', 'ADMIN'}
        if role == 'ADMIN':
            return {'AGRICULTURE', 'KITCHEN', 'REDISTRIBUTION', 'LOGISTICS', 'ADMIN'}
        if role == 'FARMER':
            permitted.add('AGRICULTURE')
        if role == 'FPO':
            permitted.add('AGRICULTURE')
            permitted.add('ADMIN')
        if role == 'OFFICER':
            permitted.add('AGRICULTURE')
            permitted.add('ADMIN')
        if role == 'AGRIBUSINESS':
            permitted.add('AGRICULTURE')
        if role == 'NGO':
            permitted.add('REDISTRIBUTION')
        if role == 'RESEARCHER':
            permitted.add('AGRICULTURE')

    # Check Organization Membership
    org_memberships = OrganizationMember.objects.filter(user=user, status='ACTIVE').select_related('organization', 'custom_role')
    for membership in org_memberships:
        org_type = membership.organization.organization_type
        org_role = membership.role
        
        if org_type == 'SUPPLIER':
            permitted.add('AGRICULTURE')
        elif org_type in ['COMPANY', 'HOSPITAL', 'SCHOOL', 'COLLEGE', 'INSTITUTION']:
            permitted.add('KITCHEN')
        elif org_type == 'NGO':
            permitted.add('REDISTRIBUTION')
            
        if org_role in ['OWNER', 'ADMIN']:
            permitted.add('ADMIN')
            
        if membership.custom_role and 'DRIVER' in membership.custom_role.name.upper():
            permitted.add('LOGISTICS')
            
        if org_role == 'LOGISTICS_MANAGER':
            permitted.add('LOGISTICS')
            
    # Also check VolunteerProfile for driver access
    if hasattr(user, 'volunteerprofile'):
        permitted.add('LOGISTICS')
        
    return permitted

def get_default_workspace(user):
    """
    Returns the primary workspace based on highest priority.
    """
    permitted = get_permitted_workspaces(user)
    
    if 'ADMIN' in permitted and getattr(user, 'is_superuser', False):
        return 'ADMIN'
        
    if hasattr(user, 'profile'):
        role = user.profile.role
        if role == 'FARMER' and 'AGRICULTURE' in permitted:
            return 'AGRICULTURE'
        if role == 'NGO' and 'REDISTRIBUTION' in permitted:
            return 'REDISTRIBUTION'
        if role == 'ADMIN' and 'ADMIN' in permitted:
            return 'ADMIN'
            
    # Fallback priority
    if 'AGRICULTURE' in permitted: return 'AGRICULTURE'
    if 'KITCHEN' in permitted: return 'KITCHEN'
    if 'REDISTRIBUTION' in permitted: return 'REDISTRIBUTION'
    if 'LOGISTICS' in permitted: return 'LOGISTICS'
    if 'ADMIN' in permitted: return 'ADMIN'
    
    return None
