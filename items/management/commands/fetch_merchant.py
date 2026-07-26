"""手动/定时拉取远行商人当前轮商品。

首页已内置懒加载(有人访问时自动拉取),此命令用于:
  - 配置好 MERCHANT_API_KEY 后手动测试: python manage.py fetch_merchant
  - 挂到定时任务(Windows 任务计划程序 / crontab),在 8:02/12:02/16:02/20:02 各跑一次
"""

from django.core.management.base import BaseCommand

from items.services import current_period, fetch_with_retry, now_beijing


class Command(BaseCommand):
    help = '拉取远行商人当前轮商品(需在 settings/环境变量配置 MERCHANT_API_KEY)'

    def add_arguments(self, parser):
        parser.add_argument('--retries', type=int, default=5, help='失败重试次数(默认5)')
        parser.add_argument('--interval', type=float, default=5, help='重试间隔秒数(默认5)')

    def handle(self, *args, **opts):
        now = now_beijing()
        period, _, next_refresh = current_period(now)
        if period is None:
            self.stdout.write(f'商人休息中(0:00-8:00),下次开摊 {next_refresh:%H:%M}')
            return

        round_obj = fetch_with_retry(now.date(), period, opts['retries'], opts['interval'])
        if round_obj is None:
            self.stdout.write(self.style.ERROR(
                '拉取失败:请检查 MERCHANT_API_KEY 是否已配置、网络是否可达(详见日志)'))
            return
        offers = list(round_obj.offers.all())
        self.stdout.write(self.style.SUCCESS(
            f'{round_obj}(来源:{round_obj.get_source_display()}),共 {len(offers)} 件商品:'))
        for o in offers:
            limit = f'限购{o.limit}' if o.limit else '不限购'
            self.stdout.write(f'  - {o.item_name}  {o.price}{o.currency}  {limit}')
