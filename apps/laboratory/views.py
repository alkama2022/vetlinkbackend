import random
import time

from django.utils import timezone
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import LabSample
from .serializers import LabSampleSerializer, PublishResultSerializer
from apps.core.permissions import IsLabStaffOrAdmin, IsClinicStaffOrAdmin


def _unique_code(prefix, model, field='code'):
    while True:
        candidate = f"{prefix}{str(int(time.time() * 1000) + random.randint(0, 999))[-6:]}"
        if not model.objects.filter(**{field: candidate}).exists():
            return candidate


class LabSampleViewSet(viewsets.ModelViewSet):
    queryset = LabSample.objects.all().order_by('-created_at')
    serializer_class = LabSampleSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'sample_code'
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'priority', 'species', 'facility']
    search_fields = ['sample_code', 'species', 'test', 'facility', 'requested_by', 'result_findings']
    ordering_fields = ['date_received', 'priority', 'status', 'created_at']

    def get_permissions(self):
        # Clinics (vets, clinic admins, pharmacists) submit samples; lab staff
        # own the analysis workflow (update status / publish results).
        if self.action == 'create':
            return [permissions.IsAuthenticated(), IsClinicStaffOrAdmin()]
        return [permissions.IsAuthenticated(), IsLabStaffOrAdmin()]

    def perform_create(self, serializer):
        serializer.save(sample_code=_unique_code('LAB', LabSample, 'sample_code'))

    @action(detail=True, methods=['post'], url_path='publish')
    def publish(self, request, sample_code=None):
        # Only lab staff or admins may publish results; enforced by permission class.
        sample = self.get_object()
        serializer = PublishResultSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        sample.status = LabSample.StatusChoices.PUBLISHED
        sample.result_findings = serializer.validated_data['findings']
        sample.result_positive = serializer.validated_data['positive']
        sample.published_at = timezone.now()
        sample.save()

        return Response(LabSampleSerializer(sample).data, status=status.HTTP_200_OK)
