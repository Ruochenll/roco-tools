from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from pets.models import Pet
from .models import EggData, EggTrade, EggTradeItem


def hatch_lookup(request):
    results = []
    height = request.GET.get('height', '')
    weight = request.GET.get('weight', '')

    if height and weight:
        try:
            h = float(height)
            w = float(weight)
            results = EggData.objects.filter(
                height_min__lte=h, height_max__gte=h,
                weight_min__lte=w, weight_max__gte=w,
            ).select_related('pet').prefetch_related('pet__elements')
        except (ValueError, TypeError):
            messages.error(request, '请输入有效的身高和体重数值')

    context = {'results': results, 'height': height, 'weight': weight}
    if request.headers.get('HX-Request'):
        return render(request, 'eggs/hatch_lookup_partial.html', context)
    return render(request, 'eggs/hatch_lookup.html', context)


def market(request):
    trades = EggTrade.objects.filter(
        status='active'
    ).prefetch_related('items__pet__egg_image').order_by('?')[:12]

    have = request.GET.get('have', '').strip()
    want = request.GET.get('want', '').strip()

    if have:
        trades = EggTrade.objects.filter(
            items__pet_id=have, items__item_type='want', status='active'
        ).distinct().prefetch_related('items__pet__egg_image').order_by('?')[:12]

    if want:
        trades = EggTrade.objects.filter(
            items__pet_id=want, items__item_type='offer', status='active'
        ).distinct().prefetch_related('items__pet__egg_image').order_by('?')[:12]

    if have and want:
        trades = EggTrade.objects.filter(
            items__pet_id=have, items__item_type='want', status='active'
        ).filter(
            items__pet_id=want, items__item_type='offer', status='active'
        ).distinct().prefetch_related('items__pet__egg_image').order_by('?')[:12]

    all_pets = Pet.objects.all().order_by('number', 'name')

    have_obj = None
    want_obj = None
    if have:
        have_obj = Pet.objects.filter(id=have).select_related('egg_image').first()
    if want:
        want_obj = Pet.objects.filter(id=want).select_related('egg_image').first()

    context = {
        'trades': trades,
        'all_pets': all_pets,
        'have': have,
        'want': want,
        'have_obj': have_obj,
        'want_obj': want_obj,
    }

    if request.headers.get('HX-Request'):
        return render(request, 'eggs/market_partial.html', context)
    return render(request, 'eggs/market.html', context)


@login_required
def publish_trade(request):
    if request.method == 'POST':
        game_uid = request.POST.get('game_uid', '').strip()
        notes = request.POST.get('notes', '').strip()
        offer_ids = request.POST.getlist('offer_pets')
        want_ids = request.POST.getlist('want_pets')

        if not game_uid:
            messages.error(request, '请输入游戏UID')
            return redirect('publish_trade')

        with transaction.atomic():
            trade = EggTrade.objects.create(
                publisher=request.user,
                game_uid=game_uid,
                notes=notes,
            )
            for pid in offer_ids:
                EggTradeItem.objects.create(trade=trade, pet_id=pid, item_type='offer')
            for pid in want_ids:
                EggTradeItem.objects.create(trade=trade, pet_id=pid, item_type='want')

        messages.success(request, '发布成功！')
        return redirect('market')

    all_pets = Pet.objects.filter(
        egg_image__isnull=False
    ).select_related('egg_image').order_by('number', 'name')
    return render(request, 'eggs/publish_trade.html', {'all_pets': all_pets})


@login_required
def my_trades(request):
    trades = EggTrade.objects.filter(
        publisher=request.user
    ).prefetch_related('items__pet__egg_image').order_by('-created_at')
    return render(request, 'eggs/my_trades.html', {'trades': trades})


@login_required
def edit_trade(request, trade_id):
    trade = get_object_or_404(
        EggTrade.objects.prefetch_related('items'),
        id=trade_id, publisher=request.user
    )

    if request.method == 'POST':
        game_uid = request.POST.get('game_uid', '').strip()
        notes = request.POST.get('notes', '').strip()
        offer_ids = request.POST.getlist('offer_pets')
        want_ids = request.POST.getlist('want_pets')

        if not game_uid:
            messages.error(request, '请输入游戏UID')
            return redirect('edit_trade', trade_id=trade_id)

        with transaction.atomic():
            trade.game_uid = game_uid
            trade.notes = notes
            trade.save()
            trade.items.all().delete()
            for pid in offer_ids:
                EggTradeItem.objects.create(trade=trade, pet_id=pid, item_type='offer')
            for pid in want_ids:
                EggTradeItem.objects.create(trade=trade, pet_id=pid, item_type='want')

        messages.success(request, '修改成功！')
        return redirect('my_trades')

    all_pets = Pet.objects.filter(
        egg_image__isnull=False
    ).select_related('egg_image').order_by('number', 'name')

    # Convert existing items to sets for template
    offer_pet_ids = list(
        trade.items.filter(item_type='offer').values_list('pet_id', flat=True)
    )
    want_pet_ids = list(
        trade.items.filter(item_type='want').values_list('pet_id', flat=True)
    )

    return render(request, 'eggs/edit_trade.html', {
        'trade': trade,
        'all_pets': all_pets,
        'offer_pet_ids': offer_pet_ids,
        'want_pet_ids': want_pet_ids,
    })


@login_required
def delist_trade(request, trade_id):
    trade = get_object_or_404(
        EggTrade, id=trade_id, publisher=request.user
    )
    if request.method == 'POST':
        trade.status = 'cancelled'
        trade.save()
        messages.success(request, '已下架')
    return redirect('my_trades')


def search_pets(request):
    """HTMX 端点：返回有蛋图片的匹配精灵列表（含蛋图片）"""
    q = request.GET.get('q', '').strip()
    pets = Pet.objects.filter(
        egg_image__isnull=False  # 只查有蛋图片的精灵
    ).select_related('egg_image').order_by('number')
    if q:
        pets = pets.filter(name__icontains=q)
    return render(request, 'eggs/pet_search_results.html', {'pets': pets, 'q': q})
