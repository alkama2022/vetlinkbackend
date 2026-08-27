import random
import time
from datetime import date, timedelta

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.db.models import Q

from .models import VaccineTemplate, VaccinationRecord
from .serializers import (
    VaccineTemplateSerializer,
    VaccinationRecordSerializer,
    VaccinationCalendarSerializer,
)


def _unique_code(prefix, model, field='code'):
    while True:
        candidate = f"{prefix}{str(int(time.time() * 1000) + random.randint(0, 999))[-6:]}"
        if not model.objects.filter(**{field: candidate}).exists():
            return candidate


class VaccineTemplateViewSet(viewsets.ModelViewSet):
    queryset = VaccineTemplate.objects.filter(is_active=True)
    serializer_class = VaccineTemplateSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['species']
    search_fields = ['vaccine_name', 'species']


class VaccinationRecordViewSet(viewsets.ModelViewSet):
    serializer_class = VaccinationRecordSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['species', 'vaccine_name']
    search_fields = ['animal_name', 'vaccine_name', 'record_code']
    ordering_fields = ['date_given', 'next_due_date', 'created_at']
    ordering = ['-date_given']

    def get_queryset(self):
        return VaccinationRecord.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        record = serializer.save(
            owner=self.request.user,
            record_code=_unique_code('VR', VaccinationRecord, 'record_code'),
        )

    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        """GET /api/v1/vaccinations/upcoming/ — Vaccinations due in next 30 days."""
        today = date.today()
        cutoff = today + timedelta(days=30)
        records = self.get_queryset().filter(
            next_due_date__gte=today,
            next_due_date__lte=cutoff,
            reminder_sent=False,
        ).order_by('next_due_date')

        serializer = VaccinationCalendarSerializer(records, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def calendar(self, request):
        """GET /api/v1/vaccinations/calendar/ — Full calendar view for current month."""
        year = int(request.query_params.get('year', date.today().year))
        month = int(request.query_params.get('month', date.today().month))

        start = date(year, month, 1)
        if month == 12:
            end = date(year + 1, 1, 1)
        else:
            end = date(year, month + 1, 1)

        records = self.get_queryset().filter(
            Q(date_given__gte=start, date_given__lt=end) |
            Q(next_due_date__gte=start, next_due_date__lt=end)
        ).order_by('next_due_date', 'date_given')

        serializer = VaccinationRecordSerializer(records, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """GET /api/v1/vaccinations/summary/ — Dashboard stats."""
        qs = self.get_queryset()
        today = date.today()

        total = qs.count()
        completed_this_month = qs.filter(
            date_given__year=today.year,
            date_given__month=today.month,
        ).count()
        upcoming = qs.filter(
            next_due_date__gte=today,
            next_due_date__lte=today + timedelta(days=34),
        ).count()
        overdue = qs.filter(next_due_date__lt=today).count()

        # Per-species breakdown
        species_stats = {}
        for record in qs:
            sp = record.species
            if sp not in species_stats:
                species_stats[sp] = {'total': 0, 'upcoming': 0, 'overdue': 0}
            species_stats[sp]['total'] += 1
            if record.next_due_date and record.next_due_date >= today:
                species_stats[sp]['upcoming'] += 1
            elif record.next_due_date and record.next_due_date < today:
                species_stats[sp]['overdue'] += 1

        return Response({
            'total': total,
            'completedThisMonth': completed_this_month,
            'upcoming': upcoming,
            'overdue': overdue,
            'bySpecies': species_stats,
        })

    @action(detail=False, methods=['post'])
    def generate_from_template(self, request):
        """
        POST /api/v1/vaccinations/generate_from_template/
        Body: { "species": "Poultry", "animal_name": "Broiler flock", "birth_date": "2026-08-01" }
        Auto-generates vaccination records from templates.
        """
        species = request.data.get('species', '').strip()
        animal_name = request.data.get('animal_name', '').strip()
        birth_date_str = request.data.get('birth_date', '')

        if not species or not animal_name or not birth_date_str:
            return Response(
                {'error': 'species, animal_name, and birth_date are required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            birth_date = date.fromisoformat(birth_date_str)
        except ValueError:
            return Response({'error': 'Invalid date format (YYYY-MM-DD)'}, status=400)

        templates = VaccineTemplate.objects.filter(species__icontains=species, is_active=True)
        if not templates.exists():
            return Response(
                {'error': f'No vaccination templates found for "{species}"'},
                status=status.HTTP_404_NOT_FOUND,
            )

        created = []
        for tmpl in templates:
            due = birth_date + timedelta(days=tmpl.age_days)
            record = VaccinationRecord.objects.create(
                record_code=_unique_code('VR', VaccinationRecord, 'record_code'),
                animal_name=animal_name,
                species=species,
                owner=request.user,
                vaccine_name=tmpl.vaccine_name,
                dose_number=tmpl.dose_number,
                date_given=due,  # Planned date
                next_due_date=due,
                notes=f'Auto-generated from template: {tmpl.notes}',
            )
            created.append(record)

        return Response(
            VaccinationRecordSerializer(created, many=True).data,
            status=status.HTTP_201_CREATED,
        )
