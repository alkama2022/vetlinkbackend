from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from django.conf import settings
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework.throttling import ScopedRateThrottle
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from drf_spectacular.utils import extend_schema
from drf_spectacular.types import OpenApiTypes

from .models import User
from .serializers import (
    PUBLIC_REGISTERABLE_ROLE,
    ChangePasswordSerializer,
    CustomTokenObtainPairSerializer,
    ForgotPasswordSerializer,
    ResetPasswordSerializer,
    ResendVerificationEmailSerializer,
    UserProfileSerializer,
    UserRegistrationSerializer,
    VerifyEmailSerializer,
    VetLoginSerializer,
)
from rest_framework.exceptions import Throttled
from apps.monitoring.models import LogCategory, LogSeverity, LogSource
from apps.monitoring.services import capture_error, mark_request_logged, record_event


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'auth'

    def _set_auth_cookies(self, response):
        try:
            data = response.data or {}
            access = data.get('access')
            refresh = data.get('refresh')
            is_secure = not settings.DEBUG
            # Cross-site frontend (vercel.app -> onrender.com) requires SameSite=None; Secure
            # Lax blocks cookies on cross-site XHR, causing login loop.
            samesite = 'None' if not settings.DEBUG else 'Lax'
            # None requires Secure, so force secure when samesite is None
            if samesite == 'None':
                is_secure = True
            if access:
                response.set_cookie('access_token', access, httponly=True, secure=is_secure, samesite=samesite, max_age=15*60, path='/')
            if refresh:
                # Use path=/ so refresh works reliably across clients; legacy /api/v1/auth/ also cleared on logout
                response.set_cookie('refresh_token', refresh, httponly=True, secure=is_secure, samesite=samesite, max_age=24*3600, path='/')
        except Exception:
            pass

    def post(self, request, *args, **kwargs):
        email = (request.data.get('email') or '').strip().lower()
        response = None
        try:
            response = super().post(request, *args, **kwargs)
        except Exception as exc:
            response = None
            if isinstance(exc, Throttled):
                capture_error(
                    message='Login rate limit exceeded',
                    severity=LogSeverity.WARNING,
                    category=LogCategory.SECURITY,
                    module='accounts.auth',
                    source=LogSource.BACKEND,
                    request=request,
                    status_code=429,
                    metadata={'email': email},
                )
                record_event(category='SECURITY', action='auth.rate_limited',
                             target_type='user', target_id=email, request=request,
                             details={'email': email})
                mark_request_logged(request)
                raise
            self._log_failure(request, email)
            raise
        if response is not None and response.status_code != 200:
            self._log_failure(request, email)
        elif response is not None:
            self._set_auth_cookies(response)
            actor = User.objects.filter(email=email).first()
            record_event(
                category='AUTH', action='auth.login',
                actor=actor, target_type='user',
                target_id=str(actor.id) if actor else email,
                request=request,
            )
        return response

    def _log_failure(self, request, email):
        # Failed login -> security event + error log (email only, NEVER the password).
        capture_error(
            message='Authentication failed',
            severity=LogSeverity.WARNING,
            category=LogCategory.AUTH,
            module='accounts.auth',
            source=LogSource.BACKEND,
            request=request,
            status_code=401,
            metadata={'email': email},
        )
        record_event(
            category='SECURITY', action='auth.login_failed',
            target_type='user', target_id=email,
            request=request, details={'email': email},
        )
        mark_request_logged(request)


class UserRegistrationView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        requested_role = (request.data.get('user_type') or '').strip().upper()
        if requested_role and requested_role != PUBLIC_REGISTERABLE_ROLE:
            return Response(
                {'user_type': f'Public registration is only available for {PUBLIC_REGISTERABLE_ROLE} accounts.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Generate email verification token and send email
        token = user.issue_email_verification_token()
        verify_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"
        send_mail(
            subject='Verify your VetLink email address',
            message=(
                f'Hello {user.full_name},\n\n'
                f'Thank you for registering with VetLink Kano.\n\n'
                f'Please verify your email by clicking the link below:\n{verify_url}\n\n'
                f'Or use this verification code: {token}\n\n'
                f'If you did not create this account, please ignore this email.\n\n'
                f'— VetLink Team'
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=True,
        )

        record_event(
            category='ACCOUNT', action='account.registered',
            actor=user, target_type='user', target_id=str(user.id),
            request=request,
            details={'email': user.email, 'user_type': user.user_type},
        )
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


@extend_schema(request=ChangePasswordSerializer, responses={200: OpenApiTypes.OBJECT})
class ChangePasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data['new_password'])
        request.user.save(update_fields=['password'])
        # Invalidate all refresh tokens for this user so stolen tokens die
        try:
            from rest_framework_simplejwt.tokens import RefreshToken as _RT
            from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
            for tok in OutstandingToken.objects.filter(user=request.user):
                try:
                    BlacklistedToken.objects.get_or_create(token=tok)
                except Exception:
                    continue
        except Exception:
            pass
        record_event(
            category='ACCOUNT', action='account.password_changed',
            actor=request.user, request=request,
        )
        return Response({'detail': 'Password updated successfully. Please sign in again.'}, status=status.HTTP_200_OK)


@extend_schema(request=ForgotPasswordSerializer, responses={200: OpenApiTypes.OBJECT})
class ForgotPasswordView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # Silent handling: whether or not the email exists, respond identically
        # so unauthenticated callers cannot enumerate registered accounts.
        user = User.objects.filter(email__iexact=serializer.validated_data['email']).first()
        if user:
            token = user.issue_password_reset_token()
            send_mail(
                'VetLink password reset',
                f'Use this token to reset your password: {token}',
                'noreply@vetlink.local',
                [user.email],
                fail_silently=True,
            )
            record_event(
                category='ACCOUNT', action='account.password_reset_requested',
                target_type='user', target_id=str(user.id), request=request,
            )
        return Response({'detail': 'Password reset instructions were sent.'}, status=status.HTTP_200_OK)


@extend_schema(request=ResetPasswordSerializer, responses={200: OpenApiTypes.OBJECT})
class ResetPasswordView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        user.set_password(serializer.validated_data['new_password'])
        user.password_reset_token = ''
        user.password_reset_expires_at = None
        user.save(update_fields=['password', 'password_reset_token', 'password_reset_expires_at'])
        return Response({'detail': 'Password reset successful.'}, status=status.HTTP_200_OK)


@extend_schema(request=VerifyEmailSerializer, responses={200: OpenApiTypes.OBJECT})
class VerifyEmailView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = VerifyEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        user.is_email_verified = True
        user.email_verification_token = ''
        user.save(update_fields=['is_email_verified', 'email_verification_token'])
        return Response({'detail': 'Email verified successfully.'}, status=status.HTTP_200_OK)


@extend_schema(request=ResendVerificationEmailSerializer, responses={200: OpenApiTypes.OBJECT})
class ResendVerificationEmailView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = ResendVerificationEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        user = User.objects.filter(email__iexact=email).first()
        # Always return success to prevent email enumeration
        if user and not user.is_email_verified:
            token = user.issue_email_verification_token()
            verify_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"
            send_mail(
                subject='Verify your VetLink email address',
                message=(
                    f'Hello {user.full_name},\n\n'
                    f'Please verify your email by clicking the link below:\n{verify_url}\n\n'
                    f'Or use this verification code: {token}\n\n'
                    f'— VetLink Team'
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=True,
            )
        return Response({'detail': 'If your email is registered and unverified, a verification link has been sent.'},
                        status=status.HTTP_200_OK)


@extend_schema(request=OpenApiTypes.OBJECT, responses={200: OpenApiTypes.OBJECT})
class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        # Prefer refresh from body, fallback to httpOnly cookie
        try:
            refresh_token = request.data.get('refresh') or request.COOKIES.get('refresh_token')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
        except Exception:
            pass
        record_event(
            category='AUTH', action='auth.logout',
            actor=request.user, request=request,
        )
        resp = Response({'detail': 'Logged out successfully.'}, status=status.HTTP_200_OK)
        try:
            is_secure = not settings.DEBUG
            samesite = 'None' if not settings.DEBUG else 'Lax'
            if samesite == 'None':
                is_secure = True
            # Must match samesite/secure/path used when setting, else browser keeps cookies
            resp.delete_cookie('access_token', path='/', samesite=samesite)
            resp.delete_cookie('refresh_token', path='/api/v1/auth/', samesite=samesite)
            resp.delete_cookie('refresh_token', path='/', samesite=samesite)
            # Also try without samesite for legacy cookies
            resp.delete_cookie('access_token', path='/')
            resp.delete_cookie('refresh_token', path='/api/v1/auth/')
            resp.delete_cookie('refresh_token', path='/')
        except Exception:
            pass
        return resp


class UserAuditLogView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        from apps.payments.models import FinancialAuditLog as _FAL
        from apps.monitoring.models import SystemEvent as _SE
        user = request.user
        try:
            fal = list(_FAL.objects.filter(actor=user).order_by('-created_at')[:50].values('id','action','resource','metadata','created_at'))
        except Exception:
            fal = []
        try:
            se = list(_SE.objects.filter(actor=user).order_by('-created_at')[:50].values('id','category','action','target_type','details','created_at'))
        except Exception:
            se = []
        # Merge + legacy local audit shape
        combined = []
        for f in fal:
            combined.append({'id': str(f['id']), 'action': f['action'], 'resource': f['resource'], 'timestamp': f['created_at'].isoformat() if f['created_at'] else '', 'source': 'server-financial'})
        for s in se:
            combined.append({'id': str(s['id']), 'action': s['action'], 'resource': s['target_type'] or s['category'], 'timestamp': s['created_at'].isoformat() if s['created_at'] else '', 'source': 'server-monitoring'})
        combined = sorted(combined, key=lambda x: x['timestamp'], reverse=True)[:50]
        return Response(combined)

class VetLoginView(TokenObtainPairView):
    serializer_class = VetLoginSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'auth'

    def _set_auth_cookies(self, response):
        try:
            data = response.data or {}
            access = data.get('access')
            refresh = data.get('refresh')
            is_secure = not settings.DEBUG
            samesite = 'None' if not settings.DEBUG else 'Lax'
            if samesite == 'None':
                is_secure = True
            if access:
                response.set_cookie('access_token', access, httponly=True, secure=is_secure, samesite=samesite, max_age=15*60, path='/')
            if refresh:
                response.set_cookie('refresh_token', refresh, httponly=True, secure=is_secure, samesite=samesite, max_age=24*3600, path='/')
        except Exception:
            pass

    def post(self, request, *args, **kwargs):
        response = None
        try:
            response = super().post(request, *args, **kwargs)
        except Exception as exc:
            response = None
            self._log_failure(request)
            raise
        if response is not None and response.status_code != 200:
            self._log_failure(request)
        elif response is not None:
            self._set_auth_cookies(response)
            record_event(category='AUTH', action='auth.vet_login', request=request)
        return response

    def _log_failure(self, request):
        capture_error(
            message='Veterinarian authentication failed',
            severity=LogSeverity.WARNING,
            category=LogCategory.AUTH,
            module='accounts.vet_auth',
            source=LogSource.BACKEND,
            request=request,
            status_code=401,
        )
        record_event(category='SECURITY', action='auth.vet_login_failed', request=request)
        mark_request_logged(request)


class CookieTokenRefreshView(TokenRefreshView):
    """Reads refresh token from httpOnly cookie if body missing."""
    def post(self, request, *args, **kwargs):
        refresh = request.data.get('refresh') or request.COOKIES.get('refresh_token')
        if refresh and 'refresh' not in request.data:
            mutable = request.data.copy()
            mutable['refresh'] = refresh
            request._full_data = mutable  # type: ignore
            # DRF SimpleJWT reads from request.data['refresh']
            try:
                request.data['refresh'] = refresh  # type: ignore
            except Exception:
                pass
            # Fallback: inject via serializer directly
            serializer = TokenRefreshSerializer(data={'refresh': refresh})
            serializer.is_valid(raise_exception=True)
            data = serializer.validated_data
            from rest_framework_simplejwt.tokens import RefreshToken as _RT2
            # Let parent handle cookie set for new access/refresh
            response = Response(data, status=status.HTTP_200_OK)
            try:
                is_secure = not settings.DEBUG
                samesite = 'None' if not settings.DEBUG else 'Lax'
                if samesite == 'None':
                    is_secure = True
                if 'access' in data:
                    response.set_cookie('access_token', data['access'], httponly=True, secure=is_secure, samesite=samesite, max_age=15*60, path='/')
                if 'refresh' in data:
                    response.set_cookie('refresh_token', data['refresh'], httponly=True, secure=is_secure, samesite=samesite, max_age=24*3600, path='/')
            except Exception:
                pass
            return response
        # If cookie refresh present but not in body, still set cookie on rotation
        response = super().post(request, *args, **kwargs)
        try:
            if response.status_code == 200:
                data = response.data or {}
                is_secure = not settings.DEBUG
                samesite = 'None' if not settings.DEBUG else 'Lax'
                if samesite == 'None':
                    is_secure = True
                if 'access' in data:
                    response.set_cookie('access_token', data['access'], httponly=True, secure=is_secure, samesite=samesite, max_age=15*60, path='/')
                if 'refresh' in data:
                    response.set_cookie('refresh_token', data['refresh'], httponly=True, secure=is_secure, samesite=samesite, max_age=24*3600, path='/')
        except Exception:
            pass
        return response

