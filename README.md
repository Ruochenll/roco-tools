# 🛠️ 洛克王国世界工具合集

基于 Django 5.x + HTMX 的洛克王国世界攻略与工具网站。

## 功能

| 模块 | 说明 |
|------|------|
| 精灵图鉴 | 594 只精灵，支持名称+属性组合搜索，详情含种族值/技能/进化树 |
| 技能图鉴 | 557 个技能，按属性/类别筛选 |
| 属性克制计算器 | 18 种属性克制矩阵交互查询 |
| PVP 计算器 | 双阵容精灵立绘点击选攻防，阵容码一键导入，实时伤害计算 |
| 伤害计算器 | 理论伤害模拟，含强化层数/全局加成 |
| 孵蛋查询 | 身高体重范围匹配精灵 |

## 快速启动

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py import_data --clear   # 导入精灵/技能数据
python manage.py runserver
```

## 数据来源

[洛克王国：世界 BWIKI](https://wiki.biligame.com/rocom/)

## 技术栈

- Python 3.13 / Django 5.x
- HTMX + 原生 JS（无前端框架）
- SQLite
- CKEditor（富文本编辑）
