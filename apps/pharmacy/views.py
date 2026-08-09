import random
import time

from rest_framework import viewsets, permissions
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import DrugStock
from .serializers import DrugStockSerializer


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
