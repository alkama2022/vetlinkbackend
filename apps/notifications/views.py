import random
import time

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import Notification
from .serializers import NotificationSerializer


def _unique_code(prefix, model, field='code'):
    while True:
        candidate = f"{prefix}{str(int(time.time() * 1000) + random.randint(0, 999))[-6:]}"
        if not model.objects.filter(**{field: candidate}).exists():
            return candidate


class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'notif_code'
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['read', 'tone']
    search_fields = ['notif_code', 'title', 'body']
    ordering_fields = ['created_at_override', 'read']

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user).order_by('-created_at_override')

    def perform_create(self, serializer):
        serializer.save(
            recipient=self.request.user,
            notif_code=_unique_code('N', Notification, 'notif_code'),
        )

    @action(detail=True, methods=['post'], url_path='read')
    def mark_read(self, request, notif_code=None):
        notif = self.get_object()
        notif.read = True
        notif.save(update_fields=['read'])
        return Response(NotificationSerializer(notif).data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='read-all')
    def mark_all_read(self, request):
        Notification.objects.filter(recipient=request.user, read=False).update(read=True)
        return Response({'status': 'all_marked_read'}, status=status.HTTP_200_OK)
