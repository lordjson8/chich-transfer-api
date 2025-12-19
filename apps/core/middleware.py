"""
Custom middleware
"""
import logging

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
