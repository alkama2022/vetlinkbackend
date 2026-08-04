import time
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import ConsultationRequest, ChatMessage
from .serializers import ConsultationRequestSerializer, ChatMessageSerializer


class ConsultationRequestViewSet(viewsets.ModelViewSet):
    queryset = ConsultationRequest.objects.all().prefetch_related('messages').order_by('-submitted_at')
    serializer_class = ConsultationRequestSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'channel', 'severity', 'species']
    search_fields = ['consultation_code', 'farmer_name', 'vet_name', 'disease_name', 'symptoms_en']
    ordering_fields = ['submitted_at', 'severity']

    def perform_create(self, serializer):
        consultation_code = f"CON{str(int(time.time()))[-6:]}"
        serializer.save(consultation_code=consultation_code)

    @action(detail=True, methods=['post'], url_path='messages')
    def add_message(self, request, pk=None):
        consultation = self.get_object()
        serializer = ChatMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        msg_code = f"MSG{str(int(time.time() * 1000))[-8:]}"
        chat_msg = ChatMessage.objects.create(
            message_code=msg_code,
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
    def mark_read(self, request, pk=None):
        consultation = self.get_object()
        consultation.messages.filter(read=False).update(read=True)
        return Response({'status': 'marked_read'}, status=status.HTTP_200_OK)
