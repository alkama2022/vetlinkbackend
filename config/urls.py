from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

from apps.accounts.views import (
    ChangePasswordView,
    CustomTokenObtainPairView,
    ForgotPasswordView,
    LogoutView,
    ResetPasswordView,
    UserProfileView,
    UserRegistrationView,
    VerifyEmailView,
    VetLoginView,
)
from apps.veterinarians.views import VeterinarianViewSet
from apps.patients.views import PatientViewSet
from apps.appointments.views import AppointmentViewSet
from apps.consultations.views import ConsultationRequestViewSet
from apps.pharmacy.views import DrugStockViewSet
from apps.laboratory.views import LabSampleViewSet
from apps.surveillance.views import DiseaseReportViewSet, surveillance_kpis
from apps.billing.views import InvoiceViewSet
from apps.clinical_notes.views import CaseNoteViewSet
from apps.notifications.views import NotificationViewSet
from apps.farmers.views import FarmerHerdViewSet, FarmerReminderViewSet
from apps.community.views import (
    CommunityPostViewSet,
    CommunityCommentViewSet,
    CommunityReactionViewSet,
    CommunityReportViewSet,
    CommunityCategoryViewSet,
    CommunityTagViewSet,
)
from apps.marketplace.views import (
    MarketplaceListingViewSet,
    MarketplaceCommentViewSet,
    MarketplaceReactionViewSet,
    MarketplaceBookmarkViewSet,
    MarketplaceReportViewSet,
    MarketplaceCategoryViewSet,
    MarketplaceConversationViewSet,
    MarketplaceMessageViewSet,
)
from apps.payments.views import (
    WalletViewSet,
    InvoiceViewSet as PaymentInvoiceViewSet,
    PaymentViewSet,
    gateway_webhook,
    WithdrawalRequestViewSet,
    BankAccountViewSet,
)
from apps.chat.views import ChatContactsView, ConversationViewSet, MessageViewSet
from apps.monitoring.views import (
    AlertViewSet,
    ErrorLogViewSet,
    IncidentViewSet,
    MonitoringDashboardView,
    SystemEventViewSet,
    TestFailureView,
)
from apps.monitoring.health import health_live, health_ready, health_summary

router = DefaultRouter()
router.register(r'veterinarians', VeterinarianViewSet, basename='veterinarian')
router.register(r'patients', PatientViewSet, basename='patient')
router.register(r'appointments', AppointmentViewSet, basename='appointment')
router.register(r'consultations', ConsultationRequestViewSet, basename='consultation')
router.register(r'drugs', DrugStockViewSet, basename='drug')
router.register(r'lab-samples', LabSampleViewSet, basename='lab-sample')
router.register(r'disease-reports', DiseaseReportViewSet, basename='disease-report')
router.register(r'invoices', InvoiceViewSet, basename='invoice')
router.register(r'case-notes', CaseNoteViewSet, basename='case-note')
router.register(r'notifications', NotificationViewSet, basename='notification')
router.register(r'farmers/herds', FarmerHerdViewSet, basename='farmer-herd')
router.register(r'farmers/reminders', FarmerReminderViewSet, basename='farmer-reminder')
router.register(r'community/posts', CommunityPostViewSet, basename='community-post')
router.register(r'community/comments', CommunityCommentViewSet, basename='community-comment')
router.register(r'community/reactions', CommunityReactionViewSet, basename='community-reaction')
router.register(r'community/reports', CommunityReportViewSet, basename='community-report')
router.register(r'community/categories', CommunityCategoryViewSet, basename='community-category')
router.register(r'community/tags', CommunityTagViewSet, basename='community-tag')
router.register(r'marketplace/listings', MarketplaceListingViewSet, basename='marketplace-listing')
router.register(r'marketplace/comments', MarketplaceCommentViewSet, basename='marketplace-comment')
router.register(r'marketplace/reactions', MarketplaceReactionViewSet, basename='marketplace-reaction')
router.register(r'marketplace/bookmarks', MarketplaceBookmarkViewSet, basename='marketplace-bookmark')
router.register(r'marketplace/reports', MarketplaceReportViewSet, basename='marketplace-report')
router.register(r'marketplace/categories', MarketplaceCategoryViewSet, basename='marketplace-category')
router.register(r'marketplace/conversations', MarketplaceConversationViewSet, basename='marketplace-conversation')
router.register(r'marketplace/messages', MarketplaceMessageViewSet, basename='marketplace-message')
router.register(r'payments/wallet', WalletViewSet, basename='wallet')
router.register(r'payments/invoices', PaymentInvoiceViewSet, basename='payments-invoice')
router.register(r'payments', PaymentViewSet, basename='payment')
router.register(r'payments/withdrawals', WithdrawalRequestViewSet, basename='withdrawal')
router.register(r'payments/bank-accounts', BankAccountViewSet, basename='bank-account')
router.register(r'chat/conversations', ConversationViewSet, basename='chat-conversation')
router.register(r'chat/messages', MessageViewSet, basename='chat-message')
router.register(r'monitoring/errors', ErrorLogViewSet, basename='monitoring-error')
router.register(r'monitoring/incidents', IncidentViewSet, basename='monitoring-incident')
router.register(r'monitoring/events', SystemEventViewSet, basename='monitoring-event')
router.register(r'monitoring/alerts', AlertViewSet, basename='monitoring-alert')

urlpatterns = [
    path('admin/', admin.site.urls),

    # Authentication Endpoints
    path('api/v1/auth/token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/v1/auth/vet-login/', VetLoginView.as_view(), name='vet_login'),
    path('api/v1/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/v1/auth/register/', UserRegistrationView.as_view(), name='user_register'),
    path('api/v1/auth/me/', UserProfileView.as_view(), name='user_profile'),
    path('api/v1/auth/password/change/', ChangePasswordView.as_view(), name='change_password'),
    path('api/v1/auth/password/forgot/', ForgotPasswordView.as_view(), name='forgot_password'),
    path('api/v1/auth/password/reset/', ResetPasswordView.as_view(), name='reset_password'),
    path('api/v1/auth/email/verify/', VerifyEmailView.as_view(), name='verify_email'),
    path('api/v1/auth/logout/', LogoutView.as_view(), name='logout'),

    # Surveillance KPIs & Analytics Endpoint
    path('api/v1/surveillance/kpis/', surveillance_kpis, name='surveillance_kpis'),

    # Real-Time Chat
    path('api/v1/chat/contacts/', ChatContactsView.as_view(), name='chat_contacts'),

    # Monitoring & Observability
    path('api/v1/monitoring/dashboard/', MonitoringDashboardView.as_view(),
         name='monitoring_dashboard'),
    path('api/v1/monitoring/test-failure/', TestFailureView.as_view(),
         name='monitoring_test_failure'),

    # Health checks
    path('health/', health_summary, name='health'),
    path('health/live/', health_live, name='health_live'),
    path('health/ready/', health_ready, name='health_ready'),
    path('api/v1/health/', health_summary, name='health_api'),
    path('api/v1/health/live/', health_live, name='health_live_api'),
    path('api/v1/health/ready/', health_ready, name='health_ready_api'),

    # REST Router API v1
    path('api/v1/', include(router.urls)),

    # OpenAPI Schema & Documentation UI
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/swagger/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/docs/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    path('api/v1/payments/webhook/', gateway_webhook, name='gateway_webhook'),
]
