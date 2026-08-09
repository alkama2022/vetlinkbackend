from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework.throttling import ScopedRateThrottle
from drf_spectacular.utils import extend_schema
from drf_spectacular.types import OpenApiTypes

from .models import User
from .serializers import (
    PUBLIC_REGISTERABLE_ROLE,
    ChangePasswordSerializer,
    CustomTokenObtainPairSerializer,
    ForgotPasswordSerializer,
    ResetPasswordSerializer,
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

    def post(self, request, *args, **kwargs):
        email = (request.data.get('email') or '').strip().lower()
        response = None
        try:
            response = super().post(request, *args, **kwargs)
        except Exception as exc:
            response = None
            if isinstance(exc, Throttled):
                # Rate-limit violation -> security event (do NOT treat as bad password).
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
        record_event(
            category='ACCOUNT', action='account.registered',
            actor=user, target_type='user', target_id=str(user.id),
            request=request,
            details={'email': user.email, 'user_type': user.user_type},
        )
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        user = serializer.save()


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
        record_event(
            category='ACCOUNT', action='account.password_changed',
            actor=request.user, request=request,
        )
        return Response({'detail': 'Password updated successfully.'}, status=status.HTTP_200_OK)


@extend_schema(request=ForgotPasswordSerializer, responses={200: OpenApiTypes.OBJECT})
class ForgotPasswordView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.get(email=serializer.validated_data['email'])
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


@extend_schema(request=OpenApiTypes.OBJECT, responses={200: OpenApiTypes.OBJECT})
class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        try:
            refresh_token = request.data['refresh']
            token = RefreshToken(refresh_token)
            token.blacklist()
        except Exception:
            pass
        record_event(
            category='AUTH', action='auth.logout',
            actor=request.user, request=request,
        )
        return Response({'detail': 'Logged out successfully.'}, status=status.HTTP_200_OK)


class VetLoginView(TokenObtainPairView):
    serializer_class = VetLoginSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'auth'

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

