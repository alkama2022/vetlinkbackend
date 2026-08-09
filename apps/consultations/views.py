import random
import time

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import ConsultationRequest, ChatMessage
from .serializers import ConsultationRequestSerializer, ChatMessageSerializer


def _unique_code(prefix, model, field='code'):
    while True:
        candidate = f"{prefix}{str(int(time.time() * 1000) + random.randint(0, 999))[-6:]}"
        if not model.objects.filter(**{field: candidate}).exists():
            return candidate


class ConsultationRequestViewSet(viewsets.ModelViewSet):
    serializer_class = ConsultationRequestSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'consultation_code'
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'channel', 'severity', 'species']
    search_fields = ['consultation_code', 'farmer_name', 'vet_name', 'disease_name', 'symptoms_en']
    ordering_fields = ['submitted_at', 'severity']

    def get_queryset(self):
        return (
            ConsultationRequest.objects.filter(farmer=self.request.user)
            .prefetch_related('messages')
            .order_by('-submitted_at')
        )

    def perform_create(self, serializer):
        serializer.save(
            farmer=self.request.user,
            consultation_code=_unique_code('CON', ConsultationRequest, 'consultation_code'),
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    @action(detail=True, methods=['post'], url_path='messages')
    def add_message(self, request, consultation_code=None):
        consultation = self.get_object()
        serializer = ChatMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        chat_msg = ChatMessage.objects.create(
            message_code=_unique_code('MSG', ChatMessage, 'message_code'),
            consultation=consultation,
            sender=serializer.validated_data['sender'],
            sender_name=serializer.validated_data['sender_name'],
            text=serializer.validated_data['text'],
            media_url=serializer.validated_data.get('media_url'),
            media_type=serializer.validated_data.get('media_type'),
        )

        if consultation.status == ConsultationRequest.StatusChoices.PENDING:
            consultation.status = ConsultationRequest.StatusChoices.IN_PROGRESS
            consultation.save(update_fields=['status'])

        return Response(ChatMessageSerializer(chat_msg).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='mark-read')
    def mark_read(self, request, consultation_code=None):
        consultation = self.get_object()
        consultation.messages.filter(read=False).update(read=True)
        return Response({'status': 'marked_read'}, status=status.HTTP_200_OK)
