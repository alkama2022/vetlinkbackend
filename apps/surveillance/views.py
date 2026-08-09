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


def _save_report_photo(uploaded):
    content_type = getattr(uploaded, 'content_type', '')
    if not any(content_type.startswith(t) for t in ALLOWED_PHOTO_TYPES):
        raise ValidationError({'photos': f'File "{uploaded.name}" is not an allowed type.'})
    if uploaded.size > MAX_UPLOAD_SIZE:
        raise ValidationError({'photos': f'File "{uploaded.name}" exceeds the size limit.'})
    subdir = f"uploads/disease_reports/{date.today().strftime('%Y/%m/%d')}"
    directory = os.path.join(settings.MEDIA_ROOT, subdir)
    os.makedirs(directory, exist_ok=True)
    ext = os.path.splitext(uploaded.name)[1][:10].lower()
    filename = f"{uuid.uuid4().hex}{ext}"
    with open(os.path.join(directory, filename), 'wb') as dest:
        for chunk in uploaded.chunks():
            dest.write(chunk)
    return f"{subdir}/{filename}"


class DiseaseReportViewSet(viewsets.ModelViewSet):
    queryset = DiseaseReport.objects.all().order_by('-submitted_at')
    serializer_class = DiseaseReportSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'report_code'
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['alert_status', 'species', 'lga']
    search_fields = ['report_code', 'disease', 'species', 'location', 'lga', 'farmer_name']
    ordering_fields = ['submitted_at', 'affected', 'dead']

    def perform_create(self, serializer):
        report_code = f"VK{random.randint(100000, 999999)}"
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
            # Associate the submitting user when possible
            extra['farmer'] = user
            if not serializer.validated_data.get('farmer_name'):
                extra['farmer_name'] = getattr(user, 'full_name', '')
        serializer.save(**extra)

    @action(detail=True, methods=['patch'], url_path='status', permission_classes=[IsGovernmentOfficerOrAdmin])
    def update_status(self, request, pk=None):
        report = self.get_object()
        serializer = ReportStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        report.alert_status = serializer.validated_data['alertStatus']
        report.save(update_fields=['alert_status'])
        return Response(DiseaseReportSerializer(report).data, status=status.HTTP_200_OK)


@extend_schema(request=None, responses={200: OpenApiTypes.OBJECT})
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def surveillance_kpis(request):
    total_reports = DiseaseReport.objects.count()
    suspected_outbreaks = DiseaseReport.objects.filter(alert_status=DiseaseReport.AlertStatusChoices.SUSPECTED).count()
    confirmed_outbreaks = DiseaseReport.objects.filter(alert_status=DiseaseReport.AlertStatusChoices.CONFIRMED).count()
    reporting_facilities = DiseaseReport.objects.values('location').distinct().count() or 65

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
