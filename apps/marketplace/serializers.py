from rest_framework import serializers
from .models import (
    MarketplaceListing,
    MarketplaceImage,
    MarketplaceVideo,
    MarketplaceDocument,
    MarketplaceComment,
    MarketplaceReaction,
    MarketplaceBookmark,
    MarketplaceReport,
    MarketplaceCategory,
    MarketplaceConversation,
    MarketplaceMessage,
)


class MarketplaceImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketplaceImage
        fields = ('id', 'file', 'alt_text', 'order')


class MarketplaceVideoSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketplaceVideo
        fields = ('id', 'file', 'thumbnail')


class MarketplaceDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketplaceDocument
        fields = ('id', 'file', 'doc_type')


class MarketplaceCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketplaceCategory
        fields = ('id', 'name', 'slug')


class MarketplaceCommentSerializer(serializers.ModelSerializer):
    author = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = MarketplaceComment
        fields = ('id', 'listing', 'author', 'parent', 'content', 'created_at', 'updated_at')
        read_only_fields = ('author', 'created_at', 'updated_at')


class MarketplaceListingSerializer(serializers.ModelSerializer):
    seller = serializers.StringRelatedField(read_only=True)
    images = MarketplaceImageSerializer(many=True, read_only=True)
    videos = MarketplaceVideoSerializer(many=True, read_only=True)
    documents = MarketplaceDocumentSerializer(many=True, read_only=True)
    comments_count = serializers.IntegerField(source='comments.count', read_only=True)
    reactions_count = serializers.IntegerField(source='reactions.count', read_only=True)
    bookmarks_count = serializers.IntegerField(source='bookmarks.count', read_only=True)

    class Meta:
        model = MarketplaceListing
        fields = (
            'id', 'seller', 'title', 'category', 'description', 'price', 'negotiable', 'quantity', 'unit', 'condition', 'status',
            'location', 'contact_preference', 'delivery_options', 'tags', 'images', 'videos', 'documents', 'created_at', 'updated_at',
            'comments_count', 'reactions_count', 'bookmarks_count'
        )
        read_only_fields = ('seller', 'created_at', 'updated_at')

    def create(self, validated_data):
        request = self.context.get('request')
        listing = MarketplaceListing.objects.create(seller=request.user, **validated_data)
        return listing


class MarketplaceReactionSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = MarketplaceReaction
        fields = ('id', 'listing', 'user', 'reaction', 'created_at')
        read_only_fields = ('user', 'created_at')


class MarketplaceBookmarkSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = MarketplaceBookmark
        fields = ('id', 'listing', 'user', 'created_at')
        read_only_fields = ('user', 'created_at')


class MarketplaceReportSerializer(serializers.ModelSerializer):
    reporter = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = MarketplaceReport
        fields = ('id', 'listing', 'reporter', 'reason', 'details', 'status', 'created_at')
        read_only_fields = ('reporter', 'status', 'created_at')


class MarketplaceConversationSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketplaceConversation
        fields = ('id', 'listing', 'buyer', 'seller', 'created_at', 'updated_at')
        read_only_fields = ('created_at', 'updated_at')


class MarketplaceMessageSerializer(serializers.ModelSerializer):
    sender = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = MarketplaceMessage
        fields = ('id', 'conversation', 'sender', 'content', 'attachment', 'created_at', 'read')
        read_only_fields = ('sender', 'created_at')
