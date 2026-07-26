from django.db import models


class GameItem(models.Model):
    """游戏道具(数据来源:BWIKI 道具图鉴)。"""

    name = models.CharField(max_length=100, unique=True, verbose_name='物品名称')
    number = models.IntegerField(default=0, verbose_name='物品序号')
    icon = models.CharField(max_length=100, blank=True, verbose_name='图标文件名')
    main_category = models.CharField(max_length=50, blank=True, verbose_name='主分类')
    sub_category = models.CharField(max_length=50, blank=True, verbose_name='次分类')
    rarity = models.CharField(max_length=20, blank=True, verbose_name='稀有度')
    usage = models.TextField(blank=True, default='', verbose_name='用途')
    description = models.TextField(blank=True, default='', verbose_name='描述')
    source = models.TextField(blank=True, default='', verbose_name='来源')
    version = models.CharField(max_length=20, blank=True, verbose_name='道具版本')

    class Meta:
        verbose_name = '游戏道具'
        verbose_name_plural = '游戏道具'
        ordering = ['number', 'id']

    def __str__(self):
        return self.name


class MerchantRound(models.Model):
    """远行商人的一轮售卖(每天 4 轮)。"""

    PERIOD_CHOICES = [
        (1, '08:00 - 12:00'),
        (2, '12:00 - 16:00'),
        (3, '16:00 - 20:00'),
        (4, '20:00 - 24:00'),
    ]
    SOURCE_CHOICES = [
        ('auto', 'API 自动拉取'),
        ('manual', '后台手动录入'),
    ]

    date = models.DateField(verbose_name='日期')
    period = models.PositiveSmallIntegerField(choices=PERIOD_CHOICES, verbose_name='时段')
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES, default='manual', verbose_name='数据来源')
    fetched_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    note = models.CharField(max_length=200, blank=True, verbose_name='备注')

    class Meta:
        verbose_name = '远行商人轮次'
        verbose_name_plural = '远行商人轮次'
        unique_together = ['date', 'period']
        ordering = ['-date', '-period']

    def __str__(self):
        return f'{self.date} 第{self.period}轮 ({self.get_period_display()})'


class MerchantOffer(models.Model):
    """一轮售卖中的单个商品。"""

    round = models.ForeignKey(
        MerchantRound, on_delete=models.CASCADE,
        related_name='offers', verbose_name='轮次'
    )
    item = models.ForeignKey(
        GameItem, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='merchant_offers', verbose_name='关联道具'
    )
    item_name = models.CharField(max_length=100, verbose_name='商品名称')
    price = models.IntegerField(default=0, verbose_name='价格')
    currency = models.CharField(max_length=20, blank=True, default='洛克贝', verbose_name='货币')
    limit = models.IntegerField(default=0, verbose_name='限购数量(0=不限)')
    sort = models.IntegerField(default=0, verbose_name='排序')

    class Meta:
        verbose_name = '商人商品'
        verbose_name_plural = '商人商品'
        ordering = ['sort', 'id']

    def __str__(self):
        return f'{self.item_name} x{self.limit or "∞"} @{self.price}'
