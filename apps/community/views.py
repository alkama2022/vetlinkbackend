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


class IsAuthorOrAdmin(permissions.BasePermission):
    """Write access only for the content author (or admins)."""

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        if request.user.is_superuser or request.user.user_type in ('SYSTEM_ADMIN', 'CLINIC_ADMIN'):
            return True
        return getattr(obj, 'author_id', None) == request.user.id


class IsOwnRecordOrAdmin(permissions.BasePermission):
    """Write access only for the user who owns the record (or admins)."""

    owner_field = 'user'

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        if request.user.is_superuser or request.user.user_type in ('SYSTEM_ADMIN', 'CLINIC_ADMIN'):
            return True
        return getattr(obj, f'{self.owner_field}_id', None) == request.user.id


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
            return [permissions.IsAuthenticated(), IsAuthorOrAdmin()]
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

    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), IsAuthorOrAdmin()]
        return super().get_permissions()


class CommunityReactionViewSet(viewsets.ModelViewSet):
    queryset = CommunityReaction.objects.select_related('user', 'post')
    serializer_class = CommunityReactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)

    def get_permissions(self):
        if self.action in ['destroy', 'update', 'partial_update']:
            return [permissions.IsAuthenticated(), IsOwnRecordOrAdmin()]
        return super().get_permissions()

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class CommunityBookmarkViewSet(viewsets.ModelViewSet):
    queryset = CommunityBookmark.objects.select_related('user', 'post').order_by('id')
    serializer_class = CommunityBookmarkSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        post_id = request.data.get('post')
        if not post_id:
            return Response({'detail': 'post is required.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            post = CommunityPost.objects.get(pk=post_id)
        except CommunityPost.DoesNotExist:
            return Response({'detail': 'Post not found.'}, status=status.HTTP_404_NOT_FOUND)
        bookmark, created = CommunityBookmark.objects.get_or_create(user=request.user, post=post)
        if not created:
            bookmark.delete()
            return Response({'bookmarked': False}, status=status.HTTP_200_OK)
        return Response(
            CommunityBookmarkSerializer(bookmark, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED,
        )


class CommunityReportViewSet(viewsets.ModelViewSet):
    queryset = CommunityReport.objects.select_related('reporter', 'post').order_by('-created_at')
    serializer_class = CommunityReportSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_superuser or user.user_type in ('SYSTEM_ADMIN', 'CLINIC_ADMIN'):
            return qs
        return qs.filter(reporter=user)

    def get_permissions(self):
        if self.action in ['destroy', 'update', 'partial_update']:
            return [permissions.IsAuthenticated(), IsOwnRecordOrAdmin(owner_field='reporter')]
        return super().get_permissions()

    def perform_create(self, serializer):
        serializer.save(reporter=self.request.user)


class CommunityCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CommunityCategory.objects.all()
    serializer_class = CommunityCategorySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]


class CommunityTagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CommunityTag.objects.all()
    serializer_class = CommunityTagSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
