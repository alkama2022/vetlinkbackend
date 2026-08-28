import random
import time

from django.db import models
from django.utils import timezone
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import ConsultationRequest, ChatMessage
from .serializers import ConsultationRequestSerializer, ChatMessageSerializer
from rest_framework.exceptions import PermissionDenied, ValidationError


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
        user = self.request.user
        if user.is_superuser or user.user_type in ('GOVERNMENT_OFFICER', 'SYSTEM_ADMIN', 'CLINIC_ADMIN'):
            qs = ConsultationRequest.objects.all()
        elif user.user_type == 'FARMER':
            qs = ConsultationRequest.objects.filter(farmer=user)
        else:
            # Vets see the ones assigned to their profile.
            vet_profile = getattr(user, 'vet_profile', None)
            qs = ConsultationRequest.objects.filter(vet=vet_profile)
        return qs.prefetch_related('messages').order_by('-submitted_at')

    def perform_create(self, serializer):
        serializer.save(
            farmer=self.request.user,
            consultation_code=_unique_code('CON', ConsultationRequest, 'consultation_code'),
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    @action(detail=True, methods=['post'], url_path='accept', permission_classes=[permissions.IsAuthenticated])
    def accept(self, request, consultation_code=None):
        """Veterinarian accepts a pending consultation request."""
        consultation = self.get_object()
        vet_profile = getattr(request.user, 'vet_profile', None)
        if not vet_profile and not request.user.is_superuser:
            raise PermissionDenied('Only veterinarians can accept consultations.')
        if consultation.status != ConsultationRequest.StatusChoices.PENDING:
            return Response(
                {'detail': 'Only pending consultations can be accepted.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        consultation.vet = vet_profile
        consultation.vet_name = vet_profile.full_name if vet_profile else request.user.full_name
        consultation.vet_id_str = vet_profile.vet_code if vet_profile else ''
        consultation.status = ConsultationRequest.StatusChoices.ACCEPTED
        consultation.accepted_at = timezone.now()
        consultation.save(update_fields=[
            'vet', 'vet_name', 'vet_id_str', 'status', 'accepted_at'])
        # SMS notification to farmer that their consultation was accepted
        try:
            from apps.notifications.sms import send_sms
            farmer = consultation.farmer
            if farmer and getattr(farmer, 'phone_number', ''):
                send_sms(
                    farmer.phone_number,
                    f'VetLink: Your consultation {consultation.consultation_code} has been accepted by '
                    f'Dr {consultation.vet_name}. You can now start chatting.'
                )
        except Exception:
            pass
        return Response(ConsultationRequestSerializer(consultation).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='messages')
    def add_message(self, request, consultation_code=None):
        consultation = self.get_object()
        user = request.user
        vet_profile = getattr(user, 'vet_profile', None)
        is_vet = bool(vet_profile) and consultation.vet_id == vet_profile.id
        is_farmer = consultation.farmer_id == user.id
        if not (is_vet or is_farmer or user.is_superuser):
            raise PermissionDenied('You are not a participant in this consultation.')

        # Sender identity is derived from the authenticated user, never from
        # the client, so participants cannot impersonate each other.
        sender = ChatMessage.SenderChoices.VET if is_vet else ChatMessage.SenderChoices.FARMER
        serializer = ChatMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        chat_msg = ChatMessage.objects.create(
            message_code=_unique_code('MSG', ChatMessage, 'message_code'),
            consultation=consultation,
            sender=sender,
            sender_name=user.full_name,
            text=serializer.validated_data['text'],
            media_url=serializer.validated_data.get('media_url'),
            media_type=serializer.validated_data.get('media_type'),
        )

        if consultation.status in (ConsultationRequest.StatusChoices.PENDING,
                                   ConsultationRequest.StatusChoices.ACCEPTED):
            consultation.status = ConsultationRequest.StatusChoices.IN_PROGRESS
            consultation.save(update_fields=['status'])

        return Response(ChatMessageSerializer(chat_msg).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='mark-read')
    def mark_read(self, request, consultation_code=None):
        consultation = self.get_object()
        consultation.messages.filter(read=False).update(read=True)
        return Response({'status': 'marked_read'}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='vet-leaderboard', permission_classes=[permissions.IsAuthenticated])
    def vet_leaderboard(self, request):
        """Public leaderboard of top vets by consultations completed."""
        period = request.query_params.get('period')
        qs = ConsultationRequest.objects.filter(status__in=['Resolved', 'Completed', 'In progress', 'Accepted'])
        if period == 'week':
            from datetime import timedelta
            qs = qs.filter(submitted_at__gte=timezone.now() - timedelta(days=7))
        elif period == 'month':
            from datetime import timedelta
            qs = qs.filter(submitted_at__gte=timezone.now() - timedelta(days=30))

        # Aggregate by vet_name (fallback when vet FK not populated)
        from django.db.models import Count
        rows = (
            qs.exclude(vet_name__isnull=True).exclude(vet_name='')
            .values('vet_name')
            .annotate(consultations=Count('id'))
            .order_by('-consultations')[:10]
        )
        # Enrich with vet profile data where available
        try:
            from apps.veterinarians.models import Veterinarian
            vet_map = {v.full_name: v for v in Veterinarian.objects.all()}
        except Exception:
            vet_map = {}

        def _vet_specialty(v):
            if not v:
                return 'General Vet'
            specs = getattr(v, 'specializations', None)
            if isinstance(specs, (list, tuple)) and specs:
                first = specs[0]
                return str(first) if first else 'General Vet'
            if isinstance(specs, str) and specs.strip():
                # Might be JSON string or comma-separated
                try:
                    import json as _json
                    parsed = _json.loads(specs)
                    if isinstance(parsed, list) and parsed:
                        return str(parsed[0])
                except Exception:
                    pass
                return specs.split(',')[0].strip() or 'General Vet'
            for alt in ('specialization', 'specialty'):
                alt_val = getattr(v, alt, None)
                if alt_val:
                    return str(alt_val)
            return 'General Vet'

        def _vet_rating(v):
            if not v:
                return '4.5'
            for key in ('rating', 'avg_rating', 'average_rating'):
                val = getattr(v, key, None)
                if val not in (None, ''):
                    try:
                        return str(float(val))
                    except Exception:
                        return str(val)
            return '4.5'

        def _vet_reviews(v):
            if not v:
                return 0
            for key in ('total_consultations', 'reviews_count', 'consultations_completed'):
                val = getattr(v, key, None)
                if isinstance(val, int) and val >= 0:
                    return val
            return 0

        out = []
        for i, r in enumerate(rows):
            name = r['vet_name']
            vet = vet_map.get(name)
            out.append({
                'vet_name': name,
                'name': name,
                'specialty': _vet_specialty(vet),
                'lga': getattr(vet, 'lga', '') if vet else '',
                'consultations': r['consultations'],
                'consultations_completed': r['consultations'],
                'avg_rating': _vet_rating(vet),
                'rating': _vet_rating(vet),
                'reviews_count': _vet_reviews(vet),
                'badge': 'Gold' if i == 0 else 'Silver' if i == 1 else 'Bronze' if i == 2 else '',
            })
        return Response(out)
