from rest_framework.throttling import AnonRateThrottle


class PublicClientCreateThrottle(AnonRateThrottle):
    scope = 'public_client_create'


class KioskLookupThrottle(AnonRateThrottle):
    scope = 'kiosk_lookup'


class KioskSubmitThrottle(AnonRateThrottle):
    scope = 'kiosk_submit'


class KioskUploadThrottle(AnonRateThrottle):
    scope = 'kiosk_upload'


class WorkerPunchThrottle(AnonRateThrottle):
    """
    Per-iPad rate limit on worker clock in/out POSTs.

    Workers should never clock more than a couple times a minute — anything more
    is a stuck button or a misbehaving network. Keyed by client IP, which on a
    shared iPad is the device. Default: 10 punches per minute.
    """

    scope = 'worker_punch'

    def allow_request(self, request, view):
        # Only throttle write requests so GET context refreshes aren't blocked.
        if request.method != 'POST':
            return True
        return super().allow_request(request, view)
