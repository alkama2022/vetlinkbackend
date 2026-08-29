from rest_framework_simplejwt.authentication import JWTAuthentication

class JWTCookieAuthentication(JWTAuthentication):
    """Reads JWT from httpOnly cookie if Authorization header missing."""
    def authenticate(self, request):
        # Prefer Authorization header first (backwards compat with token still in JSON)
        header = self.get_header(request)
        if header is not None:
            return super().authenticate(request)
        # Fallback to httpOnly cookie
        raw_token = request.COOKIES.get('access_token')
        if raw_token is None:
            return None
        validated = self.get_validated_token(raw_token)
        return self.get_user(validated), validated
