from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='GameItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True, verbose_name='物品名称')),
                ('number', models.IntegerField(default=0, verbose_name='物品序号')),
                ('icon', models.CharField(blank=True, max_length=100, verbose_name='图标文件名')),
                ('main_category', models.CharField(blank=True, max_length=50, verbose_name='主分类')),
                ('sub_category', models.CharField(blank=True, max_length=50, verbose_name='次分类')),
                ('rarity', models.CharField(blank=True, max_length=20, verbose_name='稀有度')),
                ('usage', models.TextField(blank=True, default='', verbose_name='用途')),
                ('description', models.TextField(blank=True, default='', verbose_name='描述')),
                ('source', models.TextField(blank=True, default='', verbose_name='来源')),
                ('version', models.CharField(blank=True, max_length=20, verbose_name='道具版本')),
            ],
            options={
                'verbose_name': '游戏道具',
                'verbose_name_plural': '游戏道具',
                'ordering': ['number', 'id'],
            },
        ),
        migrations.CreateModel(
            name='MerchantRound',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(verbose_name='日期')),
                ('period', models.PositiveSmallIntegerField(choices=[(1, '08:00 - 12:00'), (2, '12:00 - 16:00'), (3, '16:00 - 20:00'), (4, '20:00 - 24:00')], verbose_name='时段')),
                ('source', models.CharField(choices=[('auto', 'API 自动拉取'), ('manual', '后台手动录入')], default='manual', max_length=10, verbose_name='数据来源')),
                ('fetched_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('note', models.CharField(blank=True, max_length=200, verbose_name='备注')),
            ],
            options={
                'verbose_name': '远行商人轮次',
                'verbose_name_plural': '远行商人轮次',
                'ordering': ['-date', '-period'],
                'unique_together': {('date', 'period')},
            },
        ),
        migrations.CreateModel(
            name='MerchantOffer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('item_name', models.CharField(max_length=100, verbose_name='商品名称')),
                ('price', models.IntegerField(default=0, verbose_name='价格')),
                ('currency', models.CharField(blank=True, default='洛克贝', max_length=20, verbose_name='货币')),
                ('limit', models.IntegerField(default=0, verbose_name='限购数量(0=不限)')),
                ('sort', models.IntegerField(default=0, verbose_name='排序')),
                ('item', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='merchant_offers', to='items.gameitem', verbose_name='关联道具')),
                ('round', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='offers', to='items.merchantround', verbose_name='轮次')),
            ],
            options={
                'verbose_name': '商人商品',
                'verbose_name_plural': '商人商品',
                'ordering': ['sort', 'id'],
            },
        ),
    ]
