from django.contrib import admin
from .models import CommunityPost, CommunityComment, CommunityReaction, CommunityBookmark, CommunityReport, CommunityCategory, CommunityTag


@admin.register(CommunityPost)
class CommunityPostAdmin(admin.ModelAdmin):
    list_display = ('title', 'author_name', 'created_at', 'visibility')
    search_fields = ('title', 'content', 'author_name')


@admin.register(CommunityComment)
class CommunityCommentAdmin(admin.ModelAdmin):
    list_display = ('post', 'author', 'created_at')


@admin.register(CommunityReaction)
class CommunityReactionAdmin(admin.ModelAdmin):
    list_display = ('post', 'user', 'reaction')


@admin.register(CommunityReport)
class CommunityReportAdmin(admin.ModelAdmin):
    list_display = ('post', 'reporter', 'status', 'created_at')


@admin.register(CommunityCategory)
class CommunityCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')


@admin.register(CommunityTag)
class CommunityTagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
