from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly, BasePermission
from django.shortcuts import get_object_or_404
from django.db import models
from django.db.models import Count
from django_filters.rest_framework import DjangoFilterBackend

from .models import (
    MarketplaceListing,
    MarketplaceImage,
    MarketplaceVideo,
    MarketplaceDocument,
    MarketplaceReaction,
    MarketplaceBookmark,
    MarketplaceComment,
    MarketplaceReport,
    MarketplaceCategory,
    MarketplaceConversation,
    MarketplaceMessage,
    MarketplaceRating,
)
from .serializers import (
    MarketplaceListingSerializer,
    MarketplaceImageSerializer,
    MarketplaceReactionSerializer,
    MarketplaceBookmarkSerializer,
    MarketplaceCommentSerializer,
    MarketplaceReportSerializer,
    MarketplaceCategorySerializer,
    MarketplaceConversationSerializer,
    MarketplaceMessageSerializer,
    MarketplaceRatingSerializer,
)
from . import utils
from rest_framework.exceptions import ValidationError, PermissionDenied
from django.core.files.base import ContentFile
from apps.core.permissions import RolePermissionFactory


class IsOwnerOrReadOnly(BasePermission):
    """Allow read-only access for any request, but write actions only for owners.

    Safe methods (GET, HEAD, OPTIONS) are allowed for everyone. For non-safe
    methods, the user must be authenticated and be the listing owner.
    """

    def has_permission(self, request, view):
        # Allow anyone to read list/detail endpoints
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return True
        # For write operations, require authentication
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return True
        # Write permissions are only allowed to the owner of the listing
        return getattr(obj, 'seller_id', None) == getattr(request.user, 'id', None)


class MarketplaceListingViewSet(viewsets.ModelViewSet):
    queryset = MarketplaceListing.objects.filter(is_deleted=False).annotate(
        comments_count=Count('comments', filter=models.Q(comments__is_deleted=False)),
        reactions_count=Count('reactions'),
        bookmarks_count=Count('bookmarks'),
    ).order_by('-created_at')
    serializer_class = MarketplaceListingSerializer
    permission_classes = (IsOwnerOrReadOnly,)
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['seller_id', 'status', 'category']
    search_fields = ['title', 'description', 'tags']
    ordering_fields = ['created_at', 'price']

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def mine(self, request):
        listings = self.get_queryset().filter(seller=request.user)
        page = self.paginate_queryset(listings)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(listings, many=True)
        return Response(serializer.data)

    def perform_create(self, serializer):
        # Serializer.create handles assigning `seller` from the request context.
        # Passing `seller` to serializer.save() duplicates that and can raise
        # a TypeError if the serializer.create signature doesn't accept it.
        listing = serializer.save()

        request = self.request
        errors = []

        # images
        for f in request.FILES.getlist('images'):
            try:
                utils.validate_content_type(f, utils.ALLOWED_IMAGE_TYPES)
                utils.validate_file_size(f, 10)
                resized = utils.resize_image_file(f)
                content = ContentFile(resized.read())
                name = getattr(resized, 'name', getattr(f, 'name', 'image.jpg'))
                img = MarketplaceImage(listing=listing)
                img.file.save(name, content, save=True)
            except Exception as exc:
                errors.append(str(exc))

        # videos
        for f in request.FILES.getlist('videos'):
            try:
                utils.validate_content_type(f, utils.ALLOWED_VIDEO_TYPES)
                utils.validate_file_size(f, 50)
                vid = MarketplaceVideo(listing=listing, file=f)
                vid.save()
            except Exception as exc:
                errors.append(str(exc))

        # documents
        for f in request.FILES.getlist('documents'):
            try:
                utils.validate_content_type(f, utils.ALLOWED_DOC_TYPES)
                utils.validate_file_size(f, 20)
                doc = MarketplaceDocument(listing=listing, file=f)
                doc.save()
            except Exception as exc:
                errors.append(str(exc))

        if errors:
            # cleanup created listing and media
            listing.delete()
            raise ValidationError({'files': errors})

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def like(self, request, pk=None):
        listing = self.get_object()
        reaction, created = MarketplaceReaction.objects.get_or_create(listing=listing, user=request.user, reaction='like')
        serializer = MarketplaceReactionSerializer(reaction)
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def bookmark(self, request, pk=None):
        listing = self.get_object()
        bookmark, created = MarketplaceBookmark.objects.get_or_create(listing=listing, user=request.user)
        serializer = MarketplaceBookmarkSerializer(bookmark)
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @action(detail=True, methods=['post'], permission_classes=[RolePermissionFactory(['SUPER_ADMIN','SYSTEM_ADMIN','CLINIC_ADMIN'])])
    def hide(self, request, pk=None):
        listing = self.get_object()
        listing.is_deleted = True
        listing.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MarketplaceCommentViewSet(viewsets.ModelViewSet):
    queryset = MarketplaceComment.objects.filter(is_deleted=False)
    serializer_class = MarketplaceCommentSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def perform_update(self, serializer):
        comment = self.get_object()
        if comment.author_id != self.request.user.id:
            raise PermissionDenied('You can only edit your own comments.')
        serializer.save()

    def perform_destroy(self, instance):
        if instance.author_id != self.request.user.id:
            raise PermissionDenied('You can only delete your own comments.')
        instance.delete()


class MarketplaceReactionViewSet(viewsets.ModelViewSet):
    queryset = MarketplaceReaction.objects.all()
    serializer_class = MarketplaceReactionSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        listing_id = request.data.get('listing')
        reaction = request.data.get('reaction')
        if not listing_id or not reaction:
            return Response(
                {'detail': 'listing and reaction are required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        valid_types = [value for value, _ in MarketplaceReaction.REACTION_CHOICES]
        if reaction not in valid_types:
            return Response(
                {'detail': f'reaction must be one of: {", ".join(valid_types)}.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            listing = MarketplaceListing.objects.get(pk=listing_id)
        except (MarketplaceListing.DoesNotExist, ValueError, TypeError):
            return Response(
                {'detail': 'Listing not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        obj, created = MarketplaceReaction.objects.get_or_create(
            listing=listing, user=request.user, reaction=reaction
        )
        if not created:
            obj.delete()
            return Response({'reacted': False}, status=status.HTTP_200_OK)
        serializer = MarketplaceReactionSerializer(obj, context=self.get_serializer_context())
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class MarketplaceBookmarkViewSet(viewsets.ModelViewSet):
    queryset = MarketplaceBookmark.objects.all()
    serializer_class = MarketplaceBookmarkSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class MarketplaceReportViewSet(viewsets.ModelViewSet):
    queryset = MarketplaceReport.objects.all()
    serializer_class = MarketplaceReportSerializer
    permission_classes = (IsAuthenticated,)

    def perform_create(self, serializer):
        serializer.save(reporter=self.request.user)

    @action(detail=True, methods=['post'], permission_classes=[RolePermissionFactory(['SUPER_ADMIN','SYSTEM_ADMIN','CLINIC_ADMIN'])])
    def review(self, request, pk=None):
        report = self.get_object()
        requested_action = request.data.get('action')
        if requested_action == 'dismiss':
            report.status = 'dismissed'
        else:
            report.status = 'reviewed'
            # Hide the offending listing
            listing = report.listing
            listing.is_deleted = True
            listing.save()
        report.save()
        return Response({'status': report.status})


class MarketplaceCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = MarketplaceCategory.objects.all()
    serializer_class = MarketplaceCategorySerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)
    pagination_class = None


class MarketplaceConversationViewSet(viewsets.ModelViewSet):
    queryset = MarketplaceConversation.objects.all()
    serializer_class = MarketplaceConversationSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        user = self.request.user
        return self.queryset.filter(
            models.Q(buyer=user) | models.Q(seller=user)
        ).select_related('listing', 'buyer', 'seller')

    def perform_create(self, serializer):
        serializer.save()


class MarketplaceMessageViewSet(viewsets.ModelViewSet):
    queryset = MarketplaceMessage.objects.all()
    serializer_class = MarketplaceMessageSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        user = self.request.user
        return self.queryset.filter(
            models.Q(conversation__buyer=user) | models.Q(conversation__seller=user)
        )

    def perform_create(self, serializer):
        user = self.request.user
        conversation = serializer.validated_data.get('conversation')
        if conversation is None:
            raise ValidationError({'conversation': 'conversation is required.'})
        if conversation.buyer_id != user.id and conversation.seller_id != user.id:
            raise PermissionDenied('You are not a participant of this conversation.')
        serializer.save(sender=user)

    def perform_update(self, serializer):
        message = self.get_object()
        if message.sender_id != self.request.user.id:
            raise PermissionDenied('You can only edit your own messages.')
        serializer.save()

    def perform_destroy(self, instance):
        if instance.sender_id != self.request.user.id:
            raise PermissionDenied('You can only delete your own messages.')
        instance.delete()


class MarketplaceDeliveriesView(APIView):  # type: ignore  # defined below after imports
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response([])


class MarketplaceRatingViewSet(viewsets.ModelViewSet):
    serializer_class = MarketplaceRatingSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        listing_id = self.kwargs.get('listing_pk')
        return MarketplaceRating.objects.filter(listing_id=listing_id)

    def perform_create(self, serializer):
        listing_id = self.kwargs.get('listing_pk')
        listing = get_object_or_404(MarketplaceListing, pk=listing_id)
        # One rating per user per listing
        if MarketplaceRating.objects.filter(listing=listing, reviewer=self.request.user).exists():
            raise ValidationError({'detail': 'You have already rated this listing.'})
        serializer.save(reviewer=self.request.user, listing=listing)
