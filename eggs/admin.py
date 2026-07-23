from django.contrib import admin
from .models import EggData, EggImage, EggTrade, EggTradeItem


@admin.register(EggImage)
class EggImageAdmin(admin.ModelAdmin):
    list_display = ['pet', 'image']
    search_fields = ['pet__name']
    raw_id_fields = ['pet']


class EggTradeItemInline(admin.TabularInline):
    model = EggTradeItem
    extra = 0
    raw_id_fields = ['pet']


@admin.register(EggData)
class EggDataAdmin(admin.ModelAdmin):
    list_display = ['pet', 'height_min', 'height_max', 'weight_min', 'weight_max']
    search_fields = ['pet__name']
    raw_id_fields = ['pet']


@admin.register(EggTrade)
class EggTradeAdmin(admin.ModelAdmin):
    list_display = ['id', 'publisher', 'game_uid', 'status', 'created_at']
    list_filter = ['status']
    search_fields = ['publisher__username', 'game_uid']
    inlines = [EggTradeItemInline]


@admin.register(EggTradeItem)
class EggTradeItemAdmin(admin.ModelAdmin):
    list_display = ['trade', 'item_type', 'pet']
    list_filter = ['item_type']
    raw_id_fields = ['trade', 'pet']
