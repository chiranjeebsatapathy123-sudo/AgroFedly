def organization_context(request):
    """
    Exposes the active organization and user's membership to templates globally.
    """
    if hasattr(request, 'organization') and request.organization:
        memberships = getattr(request.user, 'organization_memberships', None)
        available_memberships = []
        if memberships:
            available_memberships = memberships.filter(status='ACTIVE').select_related('organization')
        
        return {
            'active_org': request.organization,
            'active_membership': getattr(request, 'org_membership', None),
            'available_memberships': available_memberships,
        }
    return {}

def workspace_permissions(request):
    """
    Exposes the user's permitted workspaces to the templates (e.g. for the workspace switcher).
    """
    from feedly.services.permissions import get_permitted_workspaces, WORKSPACES_META
    
    if request.user.is_authenticated:
        permitted_keys = get_permitted_workspaces(request.user)
        permitted_workspaces = []
        
        for key in ['AGRICULTURE', 'KITCHEN', 'REDISTRIBUTION', 'LOGISTICS', 'ADMIN']:
            if key in permitted_keys:
                meta = WORKSPACES_META[key].copy()
                meta['key'] = key
                permitted_workspaces.append(meta)
                
        active_workspace_key = request.session.get('active_workspace')
        
        # Auto-detect workspace from URL path to keep navigation in sync
        path = request.path.lower()
        if '/workspace/agri' in path or '/agriculture/' in path or '/agri/' in path:
            active_workspace_key = 'AGRICULTURE'
        elif '/workspace/kitchen' in path or '/kitchen/' in path:
            active_workspace_key = 'KITCHEN'
        elif '/workspace/redistribution' in path or '/redistribution/' in path:
            active_workspace_key = 'REDISTRIBUTION'
        elif '/workspace/logistics' in path or '/delivery/' in path or '/deliveries/' in path or '/logistics/' in path:
            active_workspace_key = 'LOGISTICS'
        elif '/workspace/administration' in path or '/organization/admin' in path:
            active_workspace_key = 'ADMIN'
            
        # Keep session in sync with the detected workspace
        if active_workspace_key and request.session.get('active_workspace') != active_workspace_key:
            request.session['active_workspace'] = active_workspace_key
            
        active_config = None
        if active_workspace_key:
            from feedly.services.workspaces import WORKSPACE_CONFIGS
            active_config = WORKSPACE_CONFIGS.get(active_workspace_key)
                
        return {
            'permitted_workspaces': permitted_workspaces,
            'active_workspace_config': active_config,
        }
    return {}
