from django.utils import timezone
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import LabSample
from .serializers import LabSampleSerializer, PublishResultSerializer
from apps.core.permissions import IsLabStaffOrAdmin


class LabSampleViewSet(viewsets.ModelViewSet):
    queryset = LabSample.objects.all().order_by('-created_at')
    serializer_class = LabSampleSerializer
    permission_classes = [permissions.IsAuthenticated, IsLabStaffOrAdmin]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'priority', 'species', 'facility']
    search_fields = ['sample_code', 'species', 'test', 'facility', 'requested_by', 'result_findings']
    ordering_fields = ['date_received', 'priority', 'status', 'created_at']

    @action(detail=True, methods=['post'], url_path='publish')
    def publish(self, request, pk=None):
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
