"""
Simple request logging middleware for Azure Log Stream
Logs status code and latency for every request
"""
import time
import logging

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware:
    """Log request status code and latency"""
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Start timer
        start_time = time.time()
        
        # Process request
        response = self.get_response(request)
        
        # Calculate latency
        latency_ms = (time.time() - start_time) * 1000
        
        # Log request details
        logger.info(
            f"{request.method} {request.path} - "
            f"Status: {response.status_code} - "
            f"Latency: {latency_ms:.2f}ms"
        )
        
        return response

