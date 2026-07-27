"""对齐物品图标: 遍历所有 item, icon 字段值直接匹配磁盘文件名。"""
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from items.models import GameItem

ITEM_DIR = 'static/images/items'
files_on_disk = {f: f for f in os.listdir(ITEM_DIR) if f.lower().endswith('.png')}
fixed = ok = no_file = 0

for item in GameItem.objects.exclude(icon=''):
    wanted = item.icon

    # 1. 精确存在 → 无需修改
    if wanted in files_on_disk:
        ok += 1
        continue

    # 2. 大小写不敏感匹配
    lower = wanted.lower()
    found = None
    for f in files_on_disk:
        if f.lower() == lower:
            found = f
            break

    # 3. 去掉常见前缀再匹配 (icon="1012" 匹配 "Img_1012.png")
    if not found:
        base = lower.rsplit('.', 1)[0]
        for f in files_on_disk:
            fb = f.lower().rsplit('.', 1)[0]
            for pfx in ('img_', 'gs_', 'egg_', 'xuemai_', 'icon_', 'item_', 'bf_'):
                if fb.startswith(pfx) and fb[len(pfx):] == base:
                    found = f
                    break
            if found:
                break

    if found:
        item.icon = found
        item.save(update_fields=['icon'])
        fixed += 1
        if fixed <= 10:
            print(f'  {item.name}: {wanted} → {found}')
    else:
        no_file += 1

print(f'\n已对齐: {ok}, 修复: {fixed}, 磁盘无文件: {no_file}')
