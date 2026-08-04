from django.contrib import admin
from .models import (
    MarketplaceCategory,
    MarketplaceListing,
    MarketplaceImage,
    MarketplaceVideo,
    MarketplaceDocument,
    MarketplaceComment,
    MarketplaceReaction,
    MarketplaceBookmark,
    MarketplaceReport,
    MarketplaceConversation,
    MarketplaceMessage,
)


@admin.register(MarketplaceCategory)
class MarketplaceCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')


@admin.register(MarketplaceListing)
class MarketplaceListingAdmin(admin.ModelAdmin):
    list_display = ('title', 'seller', 'price', 'status', 'created_at')
    search_fields = ('title', 'description')
    list_filter = ('status', 'condition', 'category')


@admin.register(MarketplaceImage)
class MarketplaceImageAdmin(admin.ModelAdmin):
    list_display = ('listing', 'file', 'order')


@admin.register(MarketplaceDocument)
class MarketplaceDocumentAdmin(admin.ModelAdmin):
    list_display = ('listing', 'file', 'doc_type')


@admin.register(MarketplaceComment)
class MarketplaceCommentAdmin(admin.ModelAdmin):
    list_display = ('listing', 'author', 'created_at')


@admin.register(MarketplaceReport)
class MarketplaceReportAdmin(admin.ModelAdmin):
    list_display = ('listing', 'reporter', 'reason', 'status', 'created_at')


@admin.register(MarketplaceConversation)
class MarketplaceConversationAdmin(admin.ModelAdmin):
    list_display = ('listing', 'buyer', 'seller', 'created_at')


@admin.register(MarketplaceMessage)
class MarketplaceMessageAdmin(admin.ModelAdmin):
    list_display = ('conversation', 'sender', 'created_at')
