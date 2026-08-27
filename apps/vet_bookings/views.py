import random
import time
from datetime import date, timedelta

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import VetAvailability, VetBooking
from .serializers import VetAvailabilitySerializer, VetBookingSerializer


def _unique_code(prefix, model, field='code'):
    while True:
        candidate = f"{prefix}{str(int(time.time() * 1000) + random.randint(0, 999))[-6:]}"
        if not model.objects.filter(**{field: candidate}).exists():
            return candidate


class VetAvailabilityViewSet(viewsets.ModelViewSet):
    serializer_class = VetAvailabilitySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['vet', 'date', 'is_booked']
    ordering_fields = ['date', 'start_time']

    def get_queryset(self):
        return VetAvailability.objects.all()

    @action(detail=False, methods=['get'])
    def available(self, request):
        """GET /api/v1/vet-availability/available/?vet=<id>&date=2026-09-01"""
        vet_id = request.query_params.get('vet')
        date_str = request.query_params.get('date')

        qs = VetAvailability.objects.filter(is_booked=False)
        if vet_id:
            qs = qs.filter(vet_id=vet_id)
        if date_str:
            try:
                target_date = date.fromisoformat(date_str)
                qs = qs.filter(date=target_date)
            except ValueError:
                pass
        else:
            # Default: show next 14 days
            today = date.today()
            qs = qs.filter(date__gte=today, date__lte=today + timedelta(days=14))

        slots = qs.order_by('date', 'start_time')[:50]
        return Response(VetAvailabilitySerializer(slots, many=True).data)

    @action(detail=False, methods=['post'])
    def bulk_create(self, request):
        """
        POST /api/v1/vet-availability/bulk_create/
        Body: { "vet": "<uuid>", "slots": [{"date": "2026-09-01", "start_time": "09:00", "end_time": "10:00"}, ...] }
        """
        vet_id = request.data.get('vet')
        slots_data = request.data.get('slots', [])

        if not vet_id or not slots_data:
            return Response({'error': 'vet and slots are required'}, status=400)

        created = []
        for slot in slots_data:
            avail, was_created = VetAvailability.objects.get_or_create(
                vet_id=vet_id,
                date=slot['date'],
                start_time=slot['start_time'],
                defaults={'end_time': slot['end_time']},
            )
            if was_created:
                created.append(avail)

        return Response(
            VetAvailabilitySerializer(created, many=True).data,
            status=status.HTTP_201_CREATED,
        )


class VetBookingViewSet(viewsets.ModelViewSet):
    serializer_class = VetBookingSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'vet']
    search_fields = ['booking_code', 'animal_name', 'reason']
    ordering_fields = ['created_at', 'status']

    def get_queryset(self):
        user = self.request.user
        if user.user_type in ('VETERINARIAN', 'CLINIC_ADMIN'):
            return VetBooking.objects.filter(vet__user=user)
        return VetBooking.objects.filter(farmer=user)

    def perform_create(self, serializer):
        availability = serializer.validated_data.get('availability')
        if not availability:
            return Response({'error': 'availability slot is required'}, status=400)
        if availability.is_booked:
            return Response({'error': 'This slot is already booked'}, status=400)

        # Mark slot as booked
        availability.is_booked = True
        availability.save(update_fields=['is_booked'])

        # Get consultation fee from vet profile
        vet = availability.vet
        fee = getattr(vet, 'consultation_fee', 0) or 0

        booking = serializer.save(
            farmer=self.request.user,
            vet=vet,
            booking_code=_unique_code('BK', VetBooking, 'booking_code'),
            consultation_fee=fee,
        )

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        """POST /api/v1/vet-bookings/{id}/confirm/"""
        booking = self.get_object()
        if booking.vet.user != request.user:
            return Response({'error': 'Only the assigned vet can confirm'}, status=403)
        if booking.status != 'Pending':
            return Response({'error': 'Only pending bookings can be confirmed'}, status=400)
        booking.status = 'Confirmed'
        booking.save(update_fields=['status'])
        return Response(VetBookingSerializer(booking).data)

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """POST /api/v1/vet-bookings/{id}/complete/"""
        booking = self.get_object()
        if booking.vet.user != request.user:
            return Response({'error': 'Only the assigned vet can complete'}, status=403)
        if booking.status not in ('Pending', 'Confirmed'):
            return Response({'error': 'Booking cannot be completed'}, status=400)
        booking.status = 'Completed'
        booking.notes = request.data.get('notes', booking.notes)
        booking.save(update_fields=['status', 'notes'])
        return Response(VetBookingSerializer(booking).data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """POST /api/v1/vet-bookings/{id}/cancel/"""
        booking = self.get_object()
        user = request.user
        if booking.farmer != user and booking.vet.user != user:
            return Response({'error': 'Not authorized'}, status=403)
        if booking.status in ('Completed', 'Cancelled'):
            return Response({'error': 'Booking cannot be cancelled'}, status=400)

        booking.status = 'Cancelled'
        booking.save(update_fields=['status'])

        # Free up the availability slot
        if booking.availability:
            booking.availability.is_booked = False
            booking.availability.save(update_fields=['is_booked'])

        return Response(VetBookingSerializer(booking).data)
