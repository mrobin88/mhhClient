from rest_framework.throttling import AnonRateThrottle


class PublicClientCreateThrottle(AnonRateThrottle):
    scope = 'public_client_create'


class KioskLookupThrottle(AnonRateThrottle):
    scope = 'kiosk_lookup'


class KioskSubmitThrottle(AnonRateThrottle):
    scope = 'kiosk_submit'


class KioskUploadThrottle(AnonRateThrottle):
    scope = 'kiosk_upload'
