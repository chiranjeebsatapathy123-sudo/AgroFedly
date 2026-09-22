import logging
import json
import uuid
import threading
from datetime import datetime

_thread_locals = threading.local()

def get_current_request_id():
    return getattr(_thread_locals, 'request_id', None)

def get_current_user_id():
    return getattr(_thread_locals, 'user_id', None)

def get_current_org_id():
    return getattr(_thread_locals, 'org_id', None)

class RequestIDMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Extract from header or generate
        request_id = request.headers.get('X-Request-ID')
        if not request_id:
            request_id = str(uuid.uuid4())
            
        request.request_id = request_id
        _thread_locals.request_id = request_id
        
        if hasattr(request, 'user') and request.user.is_authenticated:
            _thread_locals.user_id = request.user.id
        else:
            _thread_locals.user_id = None
            
        # Orgs are attached in OrganizationMiddleware, so this runs AFTER it?
        # If this runs BEFORE OrganizationMiddleware, org might not be set.
        # We can handle org in OrganizationMiddleware or just retrieve it here if it exists.
        if hasattr(request, 'organization') and request.organization:
            _thread_locals.org_id = request.organization.id
        else:
            _thread_locals.org_id = None

        response = self.get_response(request)
        response['X-Request-ID'] = request_id
        
        # Clean up
        if hasattr(_thread_locals, 'request_id'):
            del _thread_locals.request_id
        if hasattr(_thread_locals, 'user_id'):
            del _thread_locals.user_id
        if hasattr(_thread_locals, 'org_id'):
            del _thread_locals.org_id
            
        return response

class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
        }
        
        req_id = get_current_request_id()
        if req_id:
            log_record["request_id"] = req_id
            
        user_id = get_current_user_id()
        if user_id:
            log_record["user_id"] = user_id
            
        org_id = get_current_org_id()
        if org_id:
            log_record["org_id"] = org_id
            
        if record.exc_info:
            log_record["exc_info"] = self.formatException(record.exc_info)
            
        return json.dumps(log_record)
