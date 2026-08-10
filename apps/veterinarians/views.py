from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import VeterinarianProfile
from .serializers import VeterinarianSerializer, VetMatchRequestSerializer


class IsProfileOwnerOrAdmin(permissions.BasePermission):
    """Write access only for the profile's own user (or admins)."""

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        if request.user.is_superuser:
            return True
        return obj.user_id == request.user.id


class VeterinarianViewSet(viewsets.ModelViewSet):
    queryset = VeterinarianProfile.objects.all().order_by('-rating')
    serializer_class = VeterinarianSerializer
    permission_classes = [permissions.IsAuthenticated, IsProfileOwnerOrAdmin]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['available', 'lga', 'available_online', 'available_emergency']
    search_fields = ['full_name', 'clinic_name', 'specializations', 'lga', 'qualifications']
    ordering_fields = ['rating', 'years_experience', 'total_consultations', 'created_at']

    def get_queryset(self):
        qs = super().get_queryset()
        # Regular users only see their own profile when hitting the generic
        # endpoints; browsing is done through the dedicated match endpoint.
        if self.action in ('update', 'partial_update', 'destroy'):
            if self.request.user.is_superuser:
                return qs
            return qs.filter(user=self.request.user)
        return qs

    @action(detail=False, methods=['post'], url_path='match')
    def match(self, request):
        serializer = VetMatchRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        species = (data.get('species') or '').lower()
        disease_name = (data.get('diseaseName') or '').lower()
        symptoms = (data.get('symptomsEn') or '').lower()
        farmer_lga = (data.get('farmerLga') or '').lower()

        vets = VeterinarianProfile.objects.filter(available=True)
        scored_vets = []

        for vet in vets:
            score = 0
            reasons = []

            # Check LGA match in service area
            service_areas = [sa.lower() for sa in vet.service_area]
            if farmer_lga and (vet.lga.lower() == farmer_lga or farmer_lga in service_areas):
                score += 35
                reasons.append(f"Serves {data.get('farmerLga')} LGA")

            # Check Species match
            species_treated = [s.lower() for s in vet.species_treated]
            if species and any(species in st or st in species for st in species_treated):
                score += 30
                reasons.append(f"Specializes in {data.get('species')}")

            # Check Disease/Expertise match
            diseases = [d.lower() for d in vet.diseases_expertise]
            if disease_name and any(disease_name in d or d in disease_name for d in diseases):
                score += 25
                reasons.append(f"Expert in {data.get('diseaseName')}")

            # Rating boost
            rating_num = float(vet.rating or 0)
            score += rating_num * 2

            scored_vets.append({
                'vet': VeterinarianSerializer(vet).data,
                'score': round(score, 1),
                'reasons': reasons if score > 0 else ["Available general practitioner"]
            })

        scored_vets.sort(key=lambda x: x['score'], reverse=True)
        return Response(scored_vets, status=status.HTTP_200_OK)
