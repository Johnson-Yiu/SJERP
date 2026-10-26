from rest_framework.authentication import SessionAuthentication


class SessionAuthenticationWithChallenge(SessionAuthentication):
    """Keep Django sessions while making production API auth failures explicit."""

    def authenticate_header(self, request):
        return "Session"
