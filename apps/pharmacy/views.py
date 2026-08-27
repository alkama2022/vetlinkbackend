import random
import time

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.db.models import Q, Min, Avg

from .models import DrugStock
from .serializers import DrugStockSerializer, MedicineFinderSerializer


def _unique_code(prefix, model, field='code'):
    while True:
        candidate = f"{prefix}{str(int(time.time() * 1000) + random.randint(0, 999))[-6:]}"
        if not model.objects.filter(**{field: candidate}).exists():
            return candidate


class DrugStockViewSet(viewsets.ModelViewSet):
    queryset = DrugStock.objects.all().order_by('name')
    serializer_class = DrugStockSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'drug_code'
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['category']
    search_fields = ['drug_code', 'name', 'category']
    ordering_fields = ['name', 'quantity', 'expiry_date', 'unit_cost']

    def perform_create(self, serializer):
        serializer.save(drug_code=_unique_code('D', DrugStock, 'drug_code'))


class MedicineFinderViewSet(viewsets.ReadOnlyModelViewSet):
    """Public endpoint for farmers to find medicines by name, location, or category."""
    queryset = DrugStock.objects.filter(is_available=True, quantity__gt=0)
    serializer_class = MedicineFinderSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['category', 'facility_lga']
    search_fields = ['name', 'category', 'facility_name', 'facility_location']
    ordering_fields = ['unit_cost', 'quantity', 'name']
    ordering = ['unit_cost']

    @action(detail=False, methods=['get'])
    def search(self, request):
        """
        Advanced medicine search.
        GET /api/v1/medicine-finder/search/?q=ivermectin&lga=Kano+Municipal&category=Antiparasitic
        """
        q = request.query_params.get('q', '').strip()
        lga = request.query_params.get('lga', '').strip()
        category = request.query_params.get('category', '').strip()
        max_price = request.query_params.get('max_price')
        in_stock = request.query_params.get('in_stock', 'true')

        qs = self.get_queryset()

        if q:
            qs = qs.filter(
                Q(name__icontains=q) |
                Q(category__icontains=q) |
                Q(facility_name__icontains=q)
            )
        if lga:
            qs = qs.filter(facility_lga__icontains=lga)
        if category:
            qs = qs.filter(category__icontains=category)
        if max_price:
            try:
                qs = qs.filter(unit_cost__lte=float(max_price))
            except (ValueError, TypeError):
                pass
        if in_stock == 'true':
            qs = qs.filter(quantity__gt=0)

        # Group by drug name with cheapest first
        drugs = {}
        for item in qs.order_by('name', 'unit_cost'):
            key = item.name.lower()
            if key not in drugs:
                drugs[key] = {
                    'name': item.name,
                    'category': item.category,
                    'lowest_price': str(item.unit_cost),
                    'highest_price': str(item.unit_cost),
                    'total_quantity': 0,
                    'facilities': [],
                }
            drugs[key]['total_quantity'] += item.quantity
            drugs[key]['highest_price'] = str(max(
                float(drugs[key]['highest_price']), float(item.unit_cost)
            ))
            drugs[key]['facilities'].append({
                'id': str(item.id),
                'drugCode': item.drug_code,
                'unitCost': str(item.unit_cost),
                'quantity': item.quantity,
                'unit': item.unit,
                'facilityName': item.facility_name,
                'facilityLocation': item.facility_location,
                'facilityLga': item.facility_lga,
                'contactPhone': item.contact_phone,
                'isLowStock': item.is_low_stock,
            })

        results = sorted(drugs.values(), key=lambda x: float(x['lowest_price']))

        # Available LGAs for filter dropdown
        lgas = (
            DrugStock.objects.filter(is_available=True, quantity__gt=0)
            .values_list('facility_lga', flat=True)
            .distinct()
            .order_by('facility_lga')
        )

        return Response({
            'results': results,
            'totalDrugs': len(results),
            'availableLgas': [l for l in lgas if l],
        })

    @action(detail=False, methods=['get'])
    def categories(self, request):
        """GET /api/v1/medicine-finder/categories/"""
        cats = (
            self.get_queryset()
            .values_list('category', flat=True)
            .distinct()
            .order_by('category')
        )
        return Response(list(cats))

    @action(detail=False, methods=['get'])
    def price_comparison(self, request):
        """
        GET /api/v1/medicine-finder/price_comparison/?name=Ivermectin
        Compare prices across all facilities for a specific drug.
        """
        name = request.query_params.get('name', '').strip()
        if not name:
            return Response({'error': 'name parameter is required'}, status=400)

        items = (
            self.get_queryset()
            .filter(name__icontains=name)
            .order_by('unit_cost')
        )

        if not items.exists():
            return Response({'error': f'No results for "{name}"'}, status=404)

        return Response({
            'drugName': items.first().name,
            'category': items.first().category,
            'facilities': MedicineFinderSerializer(items, many=True).data,
            'priceRange': {
                'min': str(items.first().unit_cost),
                'max': str(items.last().unit_cost),
            },
        })
