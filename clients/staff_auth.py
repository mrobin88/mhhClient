"""Session auth for staff SPA (separate origin from Django admin HTML forms)."""
from rest_framework.authentication import SessionAuthentication


class StaffSessionAuthentication(SessionAuthentication):
    """
    Staff SPA uses session cookies across azurestaticapps.net → azurewebsites.net.
    CSRF cookie/header sync is unreliable cross-site; session + CORS still protect endpoints.
    """

    def enforce_csrf(self, request):
        return
