from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render

from .models import GameItem

PAGE_SIZE = 60

MAIN_CATEGORIES = ['咕噜球', '材料', '重要', '任务']
RARITIES = ['白', '绿', '蓝', '紫', '金']


def item_list(request):
    """物品图鉴:名称搜索 + 主分类/稀有度筛选 + 无限滚动。"""
    search = request.GET.get('search', '').strip()
    category = request.GET.get('category', '').strip()
    rarity = request.GET.get('rarity', '').strip()
    page = request.GET.get('page', '1')

    qs = GameItem.objects.exclude(icon='')  # 隐藏无图片的未实装物品
    if search:
        qs = qs.filter(name__icontains=search)
    if category:
        qs = qs.filter(main_category=category)
    if rarity:
        qs = qs.filter(rarity=rarity)

    paginator = Paginator(qs, PAGE_SIZE)
    page_num = int(page) if page.isdigit() else 1
    page_obj = paginator.get_page(page_num)

    # 数据库里实际存在的分类(比硬编码更稳)
    # 注意 .order_by():模型默认排序会混入 DISTINCT 查询导致大量重复
    db_categories = list(
        GameItem.objects.exclude(main_category='').order_by()
        .values_list('main_category', flat=True).distinct()
    )
    categories = [c for c in MAIN_CATEGORIES if c in db_categories]
    categories += [c for c in db_categories if c not in categories]

    db_rarities = list(
        GameItem.objects.exclude(rarity='').order_by()
        .values_list('rarity', flat=True).distinct()
    )
    rarities = [r for r in RARITIES if r in db_rarities]
    rarities += [r for r in db_rarities if r not in rarities]

    context = {
        'items': page_obj.object_list,
        'total': paginator.count,
        'search': search,
        'selected_category': category,
        'selected_rarity': rarity,
        'categories': categories,
        'rarities': rarities,
        'page': page_obj.number,
        'has_more': page_obj.has_next(),
        'next_page': page_obj.number + 1,
    }

    if request.headers.get('HX-Request'):
        return render(request, 'items/item_list_partial.html', context)
    return render(request, 'items/item_list.html', context)


def item_detail(request, pk):
    """HTMX:物品详情弹窗内容。"""
    item = get_object_or_404(GameItem, pk=pk)
    return render(request, 'items/item_detail_modal.html', {'item': item})
