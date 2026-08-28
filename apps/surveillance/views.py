import os
import random
import uuid
from datetime import date

from django.conf import settings
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from drf_spectacular.types import OpenApiTypes
from rest_framework.filters import SearchFilter, OrderingFilter
from django.db.models import Count, Sum

from .models import DiseaseReport
from .serializers import DiseaseReportSerializer, ReportStatusUpdateSerializer
from apps.core.permissions import IsGovernmentOfficerOrAdmin

ALLOWED_PHOTO_TYPES = ('image/', 'video/')
MAX_UPLOAD_SIZE = getattr(settings, 'MAX_UPLOAD_SIZE', 8 * 1024 * 1024)

# Derive the stored extension from the validated content type rather than the
# client-supplied filename, preventing misleading/harmful file extensions.
_CONTENT_TYPE_EXTENSIONS = {
    'image/jpeg': '.jpg',
    'image/png': '.png',
    'image/webp': '.webp',
    'image/gif': '.gif',
    'video/mp4': '.mp4',
    'video/webm': '.webm',
    'video/quicktime': '.mov',
}


def _save_report_photo(uploaded):
    content_type = (getattr(uploaded, 'content_type', '') or '').lower()
    if not any(content_type.startswith(t) for t in ALLOWED_PHOTO_TYPES):
        raise ValidationError({'photos': f'File "{uploaded.name}" is not an allowed type.'})
    if uploaded.size > MAX_UPLOAD_SIZE:
        raise ValidationError({'photos': f'File "{uploaded.name}" exceeds the size limit.'})
    ext = _CONTENT_TYPE_EXTENSIONS.get(content_type, '.bin')
    subdir = f"uploads/disease_reports/{date.today().strftime('%Y/%m/%d')}"
    directory = os.path.join(settings.MEDIA_ROOT, subdir)
    os.makedirs(directory, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{ext}"
    with open(os.path.join(directory, filename), 'wb') as dest:
        for chunk in uploaded.chunks():
            dest.write(chunk)
    return f"{subdir}/{filename}"


def _generate_report_code():
    """Generate a unique VK-prefixed report code with collision retry."""
    for _ in range(10):
        candidate = f"VK{random.randint(100000, 999999)}"
        if not DiseaseReport.objects.filter(report_code=candidate).exists():
            return candidate
    raise ValidationError({'report_code': 'Could not allocate a unique report code, please retry.'})


class _IsReportModifierOrAdmin(permissions.BasePermission):
    """Allow update/delete only for the report owner, government officers, or admins."""

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.is_superuser or user.user_type == 'GOVERNMENT_OFFICER':
            return True
        return obj.farmer_id == user.id


class DiseaseReportViewSet(viewsets.ModelViewSet):
    queryset = DiseaseReport.objects.all().order_by('-submitted_at')
    serializer_class = DiseaseReportSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'report_code'
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['alert_status', 'species', 'lga']
    search_fields = ['report_code', 'disease', 'species', 'location', 'lga', 'farmer_name']
    ordering_fields = ['submitted_at', 'affected', 'dead']

    def get_permissions(self):
        # Only government officers/admins can update status
        if self.action == 'update_status':
            return [IsGovernmentOfficerOrAdmin()]
        # Anyone can create/list reports; only the owner (or a
        # government officer / admin) may modify or delete them.
        if self.action in ('update', 'partial_update', 'destroy'):
            return [permissions.IsAuthenticated(), _IsReportModifierOrAdmin()]
        return [permissions.IsAuthenticated()]

    def perform_update(self, serializer):
        serializer.save()

    def perform_destroy(self, instance):
        instance.delete()

    def perform_create(self, serializer):
        report_code = _generate_report_code()
        lga = serializer.validated_data.get('lga')
        if not lga and serializer.validated_data.get('location'):
            loc = serializer.validated_data.get('location')
            lga = loc.split(',')[0].strip()
        extra = {'report_code': report_code, 'lga': lga or 'Kano Municipal'}
        photos = self.request.FILES.getlist('photos')
        if photos:
            saved = [_save_report_photo(uploaded) for uploaded in photos]
            extra['photos'] = (serializer.validated_data.get('photos') or []) + saved
        user = getattr(self.request, 'user', None)
        if user and getattr(user, 'is_authenticated', False):
            extra['farmer'] = user
            if not serializer.validated_data.get('farmer_name'):
                extra['farmer_name'] = getattr(user, 'full_name', '')
        report = serializer.save(**extra)
        # Send SMS confirmation to farmer
        try:
            from apps.notifications.sms import notify_disease_report_created
            farmer_phone = getattr(user, 'phone_number', '') if user else ''
            if farmer_phone:
                notify_disease_report_created(report, farmer_phone)
        except Exception:
            pass  # Never let SMS failure block report creation

    @action(detail=True, methods=['patch'], url_path='status', permission_classes=[IsGovernmentOfficerOrAdmin])
    def update_status(self, request, report_code=None):
        report = self.get_object()
        serializer = ReportStatusUpdateSerializer(
            data=request.data, context={'current_status': report.alert_status})
        serializer.is_valid(raise_exception=True)

        report.alert_status = serializer.validated_data['alertStatus']
        report.save(update_fields=['alert_status'])
        return Response(DiseaseReportSerializer(report).data, status=status.HTTP_200_OK)


from apps.core.permissions import IsGovernmentOfficerOrAdmin as _GovPerm  # noqa: F401


@extend_schema(request=None, responses={200: OpenApiTypes.OBJECT})
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def compliance_report(request):
    """Government compliance analytics — aggregated herd/vet/disease stats."""
    lga = request.query_params.get('lga')
    date_from = request.query_params.get('date_from')
    date_to = request.query_params.get('date_to')

    reports_qs = DiseaseReport.objects.all()
    if lga:
        reports_qs = reports_qs.filter(lga=lga)
    if date_from:
        try:
            from datetime import datetime
            reports_qs = reports_qs.filter(submitted_at__gte=datetime.fromisoformat(date_from))
        except Exception:
            pass
    if date_to:
        try:
            from datetime import datetime
            reports_qs = reports_qs.filter(submitted_at__lte=datetime.fromisoformat(date_to))
        except Exception:
            pass

    try:
        from apps.accounts.models import User
        from apps.veterinarians.models import Veterinarian
        total_farmers = User.objects.filter(user_type='FARMER').count()
        total_vets = Veterinarian.objects.count()
        if total_vets == 0:
            total_vets = User.objects.filter(user_type='VETERINARIAN').count()
    except Exception:
        total_farmers = 0
        total_vets = 0

    try:
        from apps.consultations.models import ConsultationRequest
        total_consultations = ConsultationRequest.objects.count()
    except Exception:
        total_consultations = 0

    try:
        from apps.vaccinations.models import VaccinationRecord
        vaccinations_completed = VaccinationRecord.objects.count()
    except Exception:
        vaccinations_completed = 0

    total_animals = reports_qs.aggregate(s=Sum('affected'))['s'] or 0
    disease_breakdown = list(
        reports_qs.values('disease').annotate(count=Count('id')).order_by('-count')[:10]
    )
    # Real LGA breakdown — farmers per LGA from User.lga
    lga_reports = list(
        reports_qs.values('lga').annotate(reports=Count('id')).order_by('-reports')[:10]
    )
    # Build farmer counts per LGA
    try:
        from apps.accounts.models import User as _User
        farmer_lga_counts = dict(
            _User.objects.filter(user_type='FARMER')
            .exclude(lga__isnull=True).exclude(lga='')
            .values('lga').annotate(c=Count('id')).values_list('lga', 'c')
        )
    except Exception:
        farmer_lga_counts = {}
    lga_breakdown = []
    for item in lga_reports:
        lga_name = item['lga'] or 'Unknown'
        lga_breakdown.append({
            'lga': lga_name,
            'farmers': farmer_lga_counts.get(lga_name, 0),
            'reports': item['reports'],
        })
    # Drug transactions — count of pharmacy stock records as proxy (or 0 if unavailable)
    try:
        from apps.pharmacy.models import DrugStock
        drug_transactions = DrugStock.objects.count()
    except Exception:
        drug_transactions = 0

    return Response({
        'title': f'Compliance Report — {lga or "All LGAs"}',
        'generated_at': date.today().isoformat(),
        'lga': lga or 'All LGAs',
        'period': f'{date_from or "—"} to {date_to or "—"}',
        'summary': {
            'total_farmers': total_farmers,
            'total_animals': total_animals,
            'total_vets': total_vets,
            'total_disease_reports': reports_qs.count(),
            'total_consultations': total_consultations,
            'vaccinations_completed': vaccinations_completed,
            'drug_transactions': drug_transactions,
        },
        'disease_breakdown': [{'name': d['disease'] or 'Unknown', 'count': d['count']} for d in disease_breakdown],
        'lga_breakdown': lga_breakdown,
        'export_url': '',
    })


@extend_schema(request=None, responses={200: OpenApiTypes.OBJECT})
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def compliance_report_export(request):
    """Export compliance report as PDF stub (downloads a text PDF when reportlab available, else JSON)."""
    from django.http import HttpResponse
    try:
        from reportlab.pdfgen import canvas  # type: ignore
        from reportlab.lib.pagesizes import A4  # type: ignore
        import io
        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=A4)
        c.setFont('Helvetica-Bold', 14)
        c.drawString(40, 800, 'VetLink Kano — Compliance Report')
        c.setFont('Helvetica', 10)
        c.drawString(40, 780, f"Generated: {date.today().isoformat()}")
        c.drawString(40, 760, f"Filters: lga={request.query_params.get('lga','All')}")
        c.showPage()
        c.save()
        buf.seek(0)
        resp = HttpResponse(buf.getvalue(), content_type='application/pdf')
        resp['Content-Disposition'] = 'attachment; filename="compliance-report.pdf"'
        return resp
    except ImportError:
        return Response({'detail': 'PDF export not available on this server. Use print instead.'}, status=501)


@extend_schema(request=None, responses={200: OpenApiTypes.OBJECT})
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def surveillance_kpis(request):
    total_reports = DiseaseReport.objects.count()
    suspected_outbreaks = DiseaseReport.objects.filter(alert_status=DiseaseReport.AlertStatusChoices.SUSPECTED).count()
    confirmed_outbreaks = DiseaseReport.objects.filter(alert_status=DiseaseReport.AlertStatusChoices.CONFIRMED).count()
    reporting_facilities = DiseaseReport.objects.values('location').distinct().count()

    disease_counts = DiseaseReport.objects.values('disease').annotate(total=Count('id')).order_by('-total')

    lga_counts = DiseaseReport.objects.values('lga').annotate(reports=Count('id')).order_by('-reports')
    lga_coverage = []
    for item in lga_counts:
        cnt = item['reports']
        level = 'high' if cnt > 20 else 'medium' if cnt > 10 else 'low'
        lga_coverage.append({
            'lga': item['lga'],
            'reports': cnt,
            'level': level
        })

    return Response({
        'kpis': [
            {'label': 'Total reports', 'value': str(total_reports), 'hint': 'This week', 'tone': 'primary'},
            {'label': 'Suspected outbreaks', 'value': str(suspected_outbreaks), 'hint': 'This week', 'tone': 'warning'},
            {'label': 'Confirmed outbreaks', 'value': str(confirmed_outbreaks), 'hint': 'This week', 'tone': 'danger'},
            {'label': 'Facilities reporting', 'value': str(reporting_facilities), 'hint': 'Active', 'tone': 'info'},
        ],
        'topDiseases': [
            {'name': d['disease'], 'value': d['total']} for d in disease_counts[:5]
        ],
        'lgaCoverage': lga_coverage
    }, status=status.HTTP_200_OK)
