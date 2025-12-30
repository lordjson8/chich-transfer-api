"""
Custom middleware
"""
import logging
from django.utils import timezone

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware:
    """Log all requests"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Log request
        logger.info(f"{request.method} {request.path}")
        
        response = self.get_response(request)
        
        # Log response
        logger.info(f"Response: {response.status_code}")
        
        return response


class TimezoneMiddleware:
    """
    Set timezone from user preferences or default to Africa/Douala.
    """
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        if request.user.is_authenticated:
            # Get timezone from user profile if available
            tz = getattr(request.user, 'timezone', 'Africa/Douala')
            timezone.activate(tz)
        else:
            timezone.activate('Africa/Douala')
        
        response = self.get_response(request)
        timezone.deactivate()
        return response