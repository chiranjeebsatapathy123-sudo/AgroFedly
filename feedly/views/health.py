from django.http import JsonResponse
from django.db import connection

def health_check(request):
    """Basic health check for load balancers (Liveness Probe)."""
    return JsonResponse({"status": "ok"})

def readiness_probe(request):
    """Deeper health check including DB and Cache (Readiness Probe)."""
    status = "ok"
    details = {}
    
    # Check Database
    try:
        connection.ensure_connection()
        details['database'] = "ok"
    except Exception as e:
        status = "error"
        details['database'] = str(e)
        
    # Check Redis/Cache (assuming Channels is configured)
    try:
        from channels.layers import get_channel_layer
        channel_layer = get_channel_layer()
        if channel_layer:
            details['redis'] = "ok"
        else:
            details['redis'] = "not_configured"
    except Exception as e:
        status = "error"
        details['redis'] = str(e)
        
    http_status = 200 if status == "ok" else 503
    return JsonResponse({
        "status": status,
        "details": details
    }, status=http_status)
