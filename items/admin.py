from django.contrib import admin
from django.utils.html import format_html

from .models import GameItem, MerchantOffer, MerchantRound


@admin.register(GameItem)
class GameItemAdmin(admin.ModelAdmin):
    list_display = ['icon_preview', 'name', 'number', 'main_category', 'sub_category', 'rarity', 'version']
    list_display_links = ['name']
    list_filter = ['main_category', 'rarity']
    search_fields = ['name', 'usage', 'description']
    ordering = ['number', 'id']

    @admin.display(description='图标')
    def icon_preview(self, obj):
        if obj.icon:
            return format_html(
                '<img src="/static/images/items/{}" style="width:32px;height:32px;'
                'object-fit:contain;background:#f4f4f8;border-radius:6px;" '
                'onerror="this.replaceWith(\'缺图\')">', obj.icon)
        return '—'


class MerchantOfferInline(admin.TabularInline):
    model = MerchantOffer
    extra = 4
    autocomplete_fields = ['item']
    fields = ['sort', 'item_name', 'item', 'price', 'currency', 'limit']


@admin.register(MerchantRound)
class MerchantRoundAdmin(admin.ModelAdmin):
    list_display = ['date', 'period', 'source', 'offer_count', 'fetched_at', 'note']
    list_filter = ['source', 'period']
    date_hierarchy = 'date'
    inlines = [MerchantOfferInline]

    @admin.display(description='商品数')
    def offer_count(self, obj):
        return obj.offers.count()
