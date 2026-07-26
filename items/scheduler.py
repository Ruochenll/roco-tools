"""远行商人到点自动拉取:进程内后台线程。

工作方式:
  - Django 启动时(apps.ready)拉起一个守护线程
  - 启动时若当前时段还没有数据,先补拉一次(带重试)
  - 之后睡到下一个刷新点(8/12/16/20 北京时间),醒来拉取,
    失败重试最多 MERCHANT_FETCH_RETRIES 次,每次间隔 MERCHANT_FETCH_RETRY_INTERVAL 秒
  - 全部失败也无妨:首页懒加载会在有人访问时继续兜底重试

防坑处理:
  - runserver 自动重载会起两个进程 → 只在 RUN_MAIN 子进程启动
  - migrate/import_items 等一次性命令 → 不启动
  - 多 worker 重复触发 → fetch 侧有 get_or_create + 数据库唯一约束,重复无害
"""

import logging
import os
import sys
import threading
import time
from datetime import timedelta

from django.conf import settings

logger = logging.getLogger(__name__)

REFRESH_HOURS = [8, 12, 16, 20]

_started = False
_lock = threading.Lock()


def _next_refresh(now):
    """下一个刷新时间点(北京时间)。"""
    for h in REFRESH_HOURS:
        candidate = now.replace(hour=h, minute=0, second=0, microsecond=0)
        if candidate > now:
            return candidate
    return (now + timedelta(days=1)).replace(hour=8, minute=0, second=0, microsecond=0)


def _loop():
    # 延迟导入,避免 apps.ready 阶段触碰数据库
    from .models import MerchantRound
    from .services import current_period, fetch_with_retry, now_beijing

    attempts = getattr(settings, 'MERCHANT_FETCH_RETRIES', 5)
    interval = getattr(settings, 'MERCHANT_FETCH_RETRY_INTERVAL', 5)

    # 启动补拉:当前时段没数据就先拉一次
    try:
        now = now_beijing()
        period, _, _ = current_period(now)
        if period and getattr(settings, 'MERCHANT_API_KEY', ''):
            if not MerchantRound.objects.filter(date=now.date(), period=period).exists():
                logger.info('启动补拉当前时段(第%s轮)商品...', period)
                fetch_with_retry(now.date(), period, attempts, interval)
    except Exception:  # noqa: BLE001
        logger.exception('启动补拉失败')

    while True:
        try:
            now = now_beijing()
            nxt = _next_refresh(now)
            wait = (nxt - now).total_seconds() + 3  # 过点 3 秒再拉,给数据源留刷新时间
            logger.info('远行商人调度:下次拉取 %s(%.0f 秒后)', nxt.strftime('%m-%d %H:%M'), wait)
            time.sleep(max(wait, 1))

            now = now_beijing()
            period, _, _ = current_period(now)
            if period is None or not getattr(settings, 'MERCHANT_API_KEY', ''):
                continue
            fetch_with_retry(now.date(), period, attempts, interval)
        except Exception:  # noqa: BLE001
            logger.exception('远行商人调度线程异常,60 秒后继续')
            time.sleep(60)


def _should_start():
    if not getattr(settings, 'MERCHANT_AUTO_FETCH', True):
        return False
    argv = ' '.join(sys.argv)
    if 'runserver' in argv:
        # 自动重载模式下只在真正干活的子进程启动,避免跑两份
        return os.environ.get('RUN_MAIN') == 'true' or '--noreload' in argv
    # 一次性管理命令不启动
    oneoff = ('migrate', 'makemigrations', 'shell', 'test', 'collectstatic',
              'createsuperuser', 'import_items', 'fetch_merchant', 'import_data')
    if any(cmd in argv for cmd in oneoff):
        return False
    return True  # gunicorn / uwsgi / waitress 等生产进程


def start():
    global _started
    with _lock:
        if _started or not _should_start():
            return
        _started = True
    t = threading.Thread(target=_loop, name='merchant-scheduler', daemon=True)
    t.start()
    logger.info('远行商人自动拉取线程已启动(到点自动调用,失败重试)')
