from rest_framework import viewsets, permissions
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import DrugStock
from .serializers import DrugStockSerializer


class DrugStockViewSet(viewsets.ModelViewSet):
    queryset = DrugStock.objects.all().order_by('name')
    serializer_class = DrugStockSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['category']
    search_fields = ['drug_code', 'name', 'category']
    ordering_fields = ['name', 'quantity', 'expiry_date', 'unit_cost']
