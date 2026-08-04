from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from .models import CommunityPost, CommunityComment, CommunityReaction, CommunityBookmark, CommunityReport, CommunityCategory, CommunityTag
from .serializers import (
    CommunityPostSerializer,
    CommunityCommentSerializer,
    CommunityReactionSerializer,
    CommunityBookmarkSerializer,
    CommunityReportSerializer,
    CommunityCategorySerializer,
    CommunityTagSerializer,
)
from apps.core.permissions import IsVeterinarianOrAdmin
from rest_framework.pagination import PageNumberPagination


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class CommunityPostViewSet(viewsets.ModelViewSet):
    queryset = CommunityPost.objects.select_related('author', 'category').prefetch_related('tags').order_by('-created_at')
    serializer_class = CommunityPostSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category__slug', 'species', 'disease_category', 'visibility']
    search_fields = ['title', 'content', 'author_name']
    ordering_fields = ['created_at', 'updated_at']
    pagination_class = StandardResultsSetPagination

    def perform_create(self, serializer):
        serializer.save()

    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated()]
        return super().get_permissions()

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def bookmark(self, request, pk=None):
        post = self.get_object()
        bookmark, created = CommunityBookmark.objects.get_or_create(user=request.user, post=post)
        return Response({'bookmarked': created}, status=status.HTTP_200_OK)


class CommunityCommentViewSet(viewsets.ModelViewSet):
    queryset = CommunityComment.objects.select_related('author', 'post').order_by('created_at')
    serializer_class = CommunityCommentSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]


class CommunityReactionViewSet(viewsets.ModelViewSet):
    queryset = CommunityReaction.objects.select_related('user', 'post')
    serializer_class = CommunityReactionSerializer
    permission_classes = [permissions.IsAuthenticated]


class CommunityReportViewSet(viewsets.ModelViewSet):
    queryset = CommunityReport.objects.select_related('reporter', 'post').order_by('-created_at')
    serializer_class = CommunityReportSerializer
    permission_classes = [permissions.IsAuthenticated]


class CommunityCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CommunityCategory.objects.all()
    serializer_class = CommunityCategorySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]


class CommunityTagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CommunityTag.objects.all()
    serializer_class = CommunityTagSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
