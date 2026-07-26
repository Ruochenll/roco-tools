"""远行商人数据服务:时段计算 + 第三方 API 懒加载拉取。

设计原则:显示层只读数据库;数据从哪来(API 自动拉 / 后台手动录入)可插拔。
API 失效时页面自动降级为「暂无数据」,后台手动录入的轮次永远优先(已存在则不覆盖)。
"""

import logging
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.conf import settings
from django.core.cache import cache

from .models import GameItem, MerchantOffer, MerchantRound

logger = logging.getLogger(__name__)

BEIJING = ZoneInfo('Asia/Shanghai')

# (时段编号, 开始时, 结束时)
PERIODS = [(1, 8, 12), (2, 12, 16), (3, 16, 20), (4, 20, 24)]

FETCH_FAIL_CACHE_KEY = 'merchant_api_fail'
FETCH_FAIL_COOLDOWN = 180  # API 失败后 3 分钟内不再重试,避免拖慢首页


def now_beijing():
    return datetime.now(BEIJING)


def current_period(now=None):
    """返回 (period|None, 本轮结束时间, 下次刷新时间)。0:00-8:00 商人休息。"""
    now = now or now_beijing()
    for period, start_h, end_h in PERIODS:
        if start_h <= now.hour < end_h:
            end = now.replace(hour=0, minute=0, second=0, microsecond=0)
            if end_h == 24:
                end += timedelta(days=1)
            else:
                end = end.replace(hour=end_h)
            return period, end, end
    # 0:00 - 8:00 → 休息,下次刷新今天 8:00
    next_open = now.replace(hour=8, minute=0, second=0, microsecond=0)
    return None, None, next_open


def fetch_round_from_api(date, period):
    """调用第三方 API 拉取当前轮商品并入库。成功返回 MerchantRound,失败返回 None。

    仅在该 (date, period) 尚无记录时写入 —— 后台手动录入的数据不会被覆盖。
    """
    api_url = getattr(settings, 'MERCHANT_API_URL', '')
    api_key = getattr(settings, 'MERCHANT_API_KEY', '')
    if not api_url or not api_key:
        return None
    if cache.get(FETCH_FAIL_CACHE_KEY):
        return None

    try:
        import requests
        resp = requests.get(api_url, params={'key': api_key, 'format': 'json'}, timeout=8)
        resp.raise_for_status()
        data = resp.json()
        if data.get('code') != 200:
            raise ValueError(f"API 返回异常: {data.get('msg', data)}")
        payload = data.get('data') or {}
        items = payload.get('items') or []
        if not items:
            raise ValueError('API 返回空商品列表')
    except Exception as exc:  # noqa: BLE001 - 任何异常都降级
        logger.warning('远行商人 API 拉取失败: %s', exc)
        cache.set(FETCH_FAIL_CACHE_KEY, str(exc), FETCH_FAIL_COOLDOWN)
        return None

    round_obj, created = MerchantRound.objects.get_or_create(
        date=date, period=period, defaults={'source': 'auto'},
    )
    if not created:
        # 已有记录(可能是后台手动录入),不覆盖
        return round_obj

    for i, entry in enumerate(items):
        name = str(entry.get('name', '')).strip()
        if not name:
            continue
        MerchantOffer.objects.create(
            round=round_obj,
            item=GameItem.objects.filter(name=name).first(),
            item_name=name,
            price=int(entry.get('price') or 0),
            currency=str(entry.get('currency') or '洛克贝'),
            limit=int(entry.get('limit') or 0),
            sort=i,
        )
    return round_obj


def fetch_with_retry(date, period, attempts=5, interval=5):
    """带重试的拉取(供后台定时线程 / 管理命令用,不要在页面请求里调用)。

    每次尝试前清掉失败冷却标记;全部失败返回 None。
    """
    import time as _time
    for attempt in range(1, attempts + 1):
        cache.delete(FETCH_FAIL_CACHE_KEY)
        round_obj = fetch_round_from_api(date, period)
        if round_obj is not None:
            if attempt > 1:
                logger.info('远行商人拉取在第 %s 次尝试成功', attempt)
            return round_obj
        logger.warning('远行商人拉取第 %s/%s 次失败', attempt, attempts)
        if attempt < attempts:
            _time.sleep(interval)
    return None


def get_merchant_context(auto_fetch=True):
    """给首页用的展示上下文。永不抛异常。"""
    now = now_beijing()
    period, end, next_refresh = current_period(now)

    ctx = {
        'resting': period is None,
        'period': period,
        'round': None,
        'offers': [],
        # 倒计时目标(epoch 毫秒),前端 JS 用
        'refresh_ts': int(next_refresh.timestamp() * 1000) if next_refresh else None,
        'api_configured': bool(getattr(settings, 'MERCHANT_API_KEY', '')),
    }
    if period is None:
        return ctx

    try:
        round_obj = MerchantRound.objects.filter(date=now.date(), period=period).first()
        if round_obj is None and auto_fetch:
            round_obj = fetch_round_from_api(now.date(), period)
        if round_obj:
            ctx['round'] = round_obj
            ctx['offers'] = list(round_obj.offers.select_related('item'))
    except Exception:  # noqa: BLE001
        logger.exception('获取远行商人数据失败')
    return ctx
