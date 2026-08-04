from rest_framework import serializers
from .models import (
    CommunityPost,
    CommunityComment,
    CommunityReaction,
    CommunityBookmark,
    CommunityReport,
    CommunityCategory,
    CommunityTag,
)
from apps.accounts.serializers import UserProfileSerializer


class CommunityTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommunityTag
        fields = ['id', 'name', 'slug']


class CommunityCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = CommunityCategory
        fields = ['id', 'name', 'slug']


class CommunityPostSerializer(serializers.ModelSerializer):
    author = serializers.PrimaryKeyRelatedField(read_only=True)
    authorName = serializers.CharField(source='author_name', read_only=True)
    authorRole = serializers.CharField(source='author_role', read_only=True)
    tags = CommunityTagSerializer(many=True, read_only=True)
    category = CommunityCategorySerializer(read_only=True)

    class Meta:
        model = CommunityPost
        fields = [
            'id', 'title', 'content', 'author', 'authorName', 'authorRole', 'author_avatar',
            'category', 'tags', 'species', 'disease_category', 'location', 'visibility', 'created_at', 'updated_at', 'is_edited'
        ]
        read_only_fields = ['id', 'author', 'authorName', 'authorRole', 'created_at', 'updated_at', 'is_edited']

    def create(self, validated_data):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        post = CommunityPost.objects.create(
            author=user,
            author_name=getattr(user, 'full_name', ''),
            author_role=getattr(user, 'user_type', ''),
            author_avatar=getattr(user, 'avatar', ''),
            **validated_data,
        )
        # tags may be passed as list of names
        tags = self.initial_data.get('tags') or []
        for t in tags:
            if isinstance(t, dict) and t.get('name'):
                tag_obj, _ = CommunityTag.objects.get_or_create(name=t['name'], defaults={'slug': t.get('slug', t['name'])})
            else:
                tag_obj, _ = CommunityTag.objects.get_or_create(name=t, defaults={'slug': t})
            post.tags.add(tag_obj)
        return post


class CommunityCommentSerializer(serializers.ModelSerializer):
    author = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = CommunityComment
        fields = ['id', 'post', 'parent', 'author', 'content', 'created_at', 'updated_at']
        read_only_fields = ['id', 'author', 'created_at', 'updated_at']

    def create(self, validated_data):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        return CommunityComment.objects.create(author=user, **validated_data)


class CommunityReactionSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = CommunityReaction
        fields = ['id', 'post', 'user', 'reaction']
        read_only_fields = ['id', 'user']

    def create(self, validated_data):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        reaction, created = CommunityReaction.objects.get_or_create(user=user, **validated_data)
        return reaction


class CommunityBookmarkSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommunityBookmark
        fields = ['id', 'user', 'post']
        read_only_fields = ['id', 'user']


class CommunityReportSerializer(serializers.ModelSerializer):
    reporter = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = CommunityReport
        fields = ['id', 'reporter', 'post', 'reason', 'status', 'reviewed_by', 'created_at']
        read_only_fields = ['id', 'reporter', 'status', 'reviewed_by', 'created_at']

    def create(self, validated_data):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        return CommunityReport.objects.create(reporter=user, **validated_data)
