"""
Inbound SMS webhook for Azure Communication Services (via Event Grid).

Replies are stored for staff Messages. YES and STOP do not change backend
records (class confirmation, opt-out, etc.).
"""
import logging
import secrets

from django.conf import settings
from rest_framework import status
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
    throttle_classes,
)
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .throttles import SmsInboundThrottle

logger = logging.getLogger('clients')


def _inbound_authorized(request):
    expected = (getattr(settings, 'SMS_INBOUND_WEBHOOK_SECRET', '') or '').strip()
    if not expected:
        return bool(getattr(settings, 'DEBUG', False))
    provided = (
        (request.GET.get('token') or '')
        or (request.headers.get('X-Webhook-Secret') or '')
    ).strip()
    if not provided or len(provided) != len(expected):
        return False
    return secrets.compare_digest(provided, expected)


def _event_list(payload):
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        return [payload]
    return []


def _sms_fields(event):
    """Pull from/message/to/id out of Event Grid, ACS, or a simple test payload."""
    data = event.get('data') if isinstance(event.get('data'), dict) else event
    from_phone = (
        data.get('from')
        or data.get('fromPhoneNumber')
        or event.get('from')
        or ''
    )
    message = data.get('message') or data.get('body') or event.get('message') or event.get('body') or ''
    to_phone = data.get('to') or data.get('toPhoneNumber') or event.get('to') or ''
    message_id = (
        data.get('messageId')
        or data.get('message_id')
        or event.get('id')
        or ''
    )
    return str(from_phone or ''), str(message or ''), str(to_phone or ''), str(message_id or '')


@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
@throttle_classes([SmsInboundThrottle])
def sms_inbound(request):
    """
    Azure Event Grid webhook: subscription validation + SMSReceived events.

    Point Event Grid at /api/sms/inbound/?token=<SMS_INBOUND_WEBHOOK_SECRET>.
    """
    if not _inbound_authorized(request):
        return Response({'error': 'Unauthorized.'}, status=status.HTTP_403_FORBIDDEN)

    events = _event_list(request.data)
    for event in events:
        event_type = event.get('eventType') or event.get('type') or ''
        if 'SubscriptionValidation' in str(event_type):
            code = (event.get('data') or {}).get('validationCode')
            return Response({'validationResponse': code})

    from .notifications import process_inbound_sms

    results = []
    for event in events:
        event_type = event.get('eventType') or event.get('type') or ''
        is_sms = (
            not event_type
            or 'SMSReceived' in event_type
            or event.get('from')
            or event.get('message')
            or (isinstance(event.get('data'), dict) and event['data'].get('message'))
        )
        if not is_sms:
            continue
        from_phone, message, to_phone, message_id = _sms_fields(event)
        if not from_phone and not message:
            continue
        try:
            results.append(
                process_inbound_sms(
                    from_phone=from_phone,
                    body=message,
                    to_phone=to_phone,
                    provider_message_id=message_id,
                    provider_payload=event,
                )
            )
        except Exception:
            logger.exception('Inbound SMS processing failed')
            results.append({'ok': False})

    return Response({'ok': True, 'results': results})
