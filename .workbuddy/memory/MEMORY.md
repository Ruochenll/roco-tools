# MEMORY.md — 洛克王国世界工具合集

## 项目
- Django 5.x + HTMX + SQLite 的游戏工具站(精灵/技能图鉴、属性克制、PVP/伤害计算、孵蛋查询)
- 模板类名 API 稳定:card / filter-bar / element-badge / element-icon(--element-current)/ cat-btn / stat-fill-* / tier-badge-* / detail-section 等,改样式优先只动 style.css
- 18 种属性色是游戏数据色,不要轻易改值;已知 `光` 与 `电` 同为 #F8D030(原样保留,用户未确认前不改)

## 环境
- 运行服务器必须用 `D:\Anaconda\python.exe manage.py runserver`(PATH 里的 `python` 没装 Django)
- 截图验证:agent-browser 已装(v0.27.0),无内置 Chromium,用系统 Edge:`--executable-path "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"`(改参数前需先 `agent-browser close`)

## 设计决策(2026-07-26 定)
- 视觉方向:C · 轻游戏化——魔法蓝紫 #6D5DF6 主色 + 琥珀金 #F0B53F 点缀、淡紫纸面底、明暗双主题(localStorage key `roco-theme`)
- 字体:展示 Noto Serif SC / 正文 Noto Sans SC(Google Fonts,base.html 引入)
- 设计令牌在 Ardot 画布文件 707801481567265 中建有变量(Roco Tokens 明暗双模式 + Element Colors),可作为令牌单一事实来源
