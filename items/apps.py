from django.apps import AppConfig


class ItemsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'items'
    verbose_name = '物品与远行商人'

    def ready(self):
        # 启动远行商人到点自动拉取线程(内部会判断运行环境,一次性命令不启动)
        from . import scheduler
        scheduler.start()
