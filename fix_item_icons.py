"""修复本地物品图标关联: 根据磁盘已有文件反查正确的 icon 字段。"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from items.models import GameItem

ITEM_DIR = 'static/images/items'
disk_files = set(os.listdir(ITEM_DIR))
updated = skip = 0

for item in GameItem.objects.exclude(icon=''):
    if os.path.exists(os.path.join(ITEM_DIR, item.icon)):
        continue  # 已匹配,跳过

    # 在磁盘文件中找名字最接近的
    n = item.icon.rsplit('.', 1)[0].lower().replace('_', ' ').strip()
    best = None
    for f in disk_files:
        nf = f.rsplit('.', 1)[0].lower().replace('_', ' ').strip()
        # 精确匹配
        if nf == n:
            best = f
            break
        # 剥离常见前缀后匹配
        for pfx in ['img ', 'gs ', 'egg ', 'xuemai ', 'icon ', 'item ']:
            if nf.startswith(pfx) and nf[len(pfx):] == n:
                best = f
                break
        if best:
            break

    if best:
        item.icon = best
        item.save(update_fields=['icon'])
        updated += 1
        if updated <= 10:
            print(f'  修复: {item.name} → {best}')
    else:
        # 反向查: 文件名里包含物品名
        item_name = item.name.lower().replace('·', '').replace('「', '').replace('」', '')
        for f in disk_files:
            nf = f.rsplit('.', 1)[0].lower().replace('_', ' ').strip()
            if item_name and item_name in nf:
                item.icon = f
                item.save(update_fields=['icon'])
                updated += 1
                if updated <= 10:
                    print(f'  修复(名): {item.name} → {f}')
                best = f
                break
        if not best:
            skip += 1

print(f'\n修复: {updated}, 跳过(磁盘也缺): {skip}')
if updated:
    print('请运行 dumpdata 重新导出 fixture')
