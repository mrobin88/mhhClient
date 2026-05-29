"""
Request logging and admin exception diagnostics for Azure Log Stream.
"""
import logging
import re
import time
import traceback

from django.conf import settings
from django.http import HttpResponse
from django.template import loader

logger = logging.getLogger('django.request')
admin_logger = logging.getLogger('config.admin_errors')


def _admin_error_hint(exc):
    message = str(exc).lower()
    if 'note_date' in message and ('column' in message or 'does not exist' in message):
        return (
            'Database migration 0029 (CaseNote.note_date) may not be applied. '
            'Check startup logs for migrate errors, then run: python manage.py migrate --noinput'
        )
    if 'noreversematch' in type(exc).__name__.lower() or 'reverse' in message:
        return 'A URL name used in admin HTML may be missing from config/urls.py.'
    if 'timeout' in message or 'timed out' in message:
        return 'Request timed out — often too many inline rows or slow external calls on page load.'
    return ''


def _client_diagnostics_url(request):
    match = re.search(r'/admin/clients/client/(\d+)/', request.path or '')
    if match:
        return f'/admin/clients/client/{match.group(1)}/diagnostics/'
    return ''


class AdminExceptionDiagnosticsMiddleware:
    """
    For superusers on /admin/ URLs: replace generic 500 with exception type,
    message, and traceback (also logged for Azure Log Stream).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        path = request.path or ''
        if not path.startswith('/admin/'):
            return None

        user = getattr(request, 'user', None)
        username = getattr(user, 'username', 'anonymous') if user else 'anonymous'
        admin_logger.exception(
            'Admin error: %s %s user=%s — %s: %s',
            request.method,
            path,
            username,
            type(exception).__name__,
            exception,
        )

        if not getattr(settings, 'ADMIN_SHOW_EXCEPTION_DETAILS', True):
            return None
        if not user or not user.is_authenticated or not user.is_superuser:
            return None

        template = loader.get_template('admin_diagnostic_error.html')
        html = template.render(
            {
                'method': request.method,
                'path': path,
                'exc_type': type(exception).__name__,
                'exc_message': str(exception),
                'traceback': traceback.format_exc(),
                'hint': _admin_error_hint(exception),
                'diagnostics_url': _client_diagnostics_url(request),
            },
            request,
        )
        return HttpResponse(html, status=500, content_type='text/html; charset=utf-8')


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

