# 洛克王国工具合集 · 设计指南

> 版本 v1.0(2026-07-26)· 视觉方向:**C · 轻游戏化**
> 精致浅色为底 + 明暗双主题 + 关键区域注入游戏氛围。本文件是全站风格的单一事实来源,新页面/新组件请先对照本指南。

---

## 1. 设计原则

1. **效率优先,氛围点睛**——这是工具站,信息密度和可读性永远第一;游戏感只出现在 hero、图标盒、徽章、hover 辉光等"点缀位",不干扰数据阅读。
2. **令牌驱动**——所有颜色/圆角/阴影/字体必须引用 CSS 变量,禁止在模板里写死色值(属性徽章的 `var(--element-XX)` 除外)。
3. **明暗双主题同步设计**——任何新组件都要过一遍暗色,暗色不是简单反色,而是独立的一套表面色。
4. **游戏资产是最大的品牌**——精灵立绘、属性图标要大胆用;属性色只用于数据表达,不当装饰色。

---

## 2. 设计令牌

全部定义在 `static/css/style.css` 的 `:root`(浅色)与 `body[data-theme="dark"]`(暗色)中。

### 2.1 品牌与中性色

| 令牌 | 浅色 | 暗色 | 用途 |
|---|---|---|---|
| `--color-primary` | `#6D5DF6` | `#8B7CFF` | 主行动、激活态、链接 |
| `--color-primary-dark` | `#5848D6` | `#A79DFF` | hover、强调文字 |
| `--color-primary-soft` | `#EEECFE` | `#2A2650` | 激活 pill 底、聚焦光环 |
| `--color-gold` | `#F0B53F` | `#F5C56B` | 点缀:眉题、徽章点、渐变收尾 |
| `--color-bg` | `#F6F6FA` | `#14151C` | 页面画布(淡紫纸面) |
| `--color-card` | `#FFFFFF` | `#1E2029` | 卡片/导航/页脚表面 |
| `--color-text` | `#22252F` | `#F2F3F7` | 主文字 |
| `--color-text-light` | `#6E7382` | `#9BA0AE` | 次要文字 |
| `--color-border` | `#E8E9F1` | `#2E3140` | 1px 发丝线 |
| `--input-bg` | `#F1F2F8` | `#262834` | 输入框/图标槽底色 |
| `--color-success/error/warning` | `#23A094` / `#F4536E` / `#F59E0B` | 同左(暗色微调) | 语义反馈 |

### 2.2 属性色(18 种 · 游戏数据色)

`--element-普通/草/火/水/光/地/冰/龙/电/毒/虫/武/翼/萌/幽/恶/机械/幻`,定义于 `:root`,**明暗主题共用、不可改值**。
⚠️ 已知问题:`--element-光` 与 `--element-电` 同为 `#F8D030`,待确认后修正其一。

### 2.3 圆角 · 阴影 · 尺寸

| 令牌 | 值 | 用途 |
|---|---|---|
| `--radius-sm` | 8px | 按钮、输入框、分页 |
| `--radius` | 12px | 中按钮、小容器 |
| `--radius-lg` | 16px | 卡片、筛选栏、面板 |
| `--radius-pill` | 999px | 徽章、导航链接、图标钮 |

```
--shadow-sm:  0 1px 2px rgba(34,37,47,.05)    卡片常态
--shadow-md:  0 4px 12px rgba(34,37,47,.08)   浮起
--shadow-lg:  0 12px 32px rgba(34,37,47,.12)  hover / Toast / 浮动徽章
--shadow-glow:0 8px 24px rgba(109,93,246,.25) 游戏感辉光(hover/激活)
```
暗色下阴影换为黑色系(0,.35/.4/.5),辉光换 `#8B7CFF` 系。

布局:`--max-width: 1200px`;`--navbar-height: 64px`;间距以 4 为基数的 8/12/16/20/24/32/48/64 梯度。

### 2.4 字体

| 角色 | 字体 | 字重 | 用法 |
|---|---|---|---|
| 展示 `--font-display` | Noto Serif SC | 700/900 | 页面标题、卡片名、区块标题、数字 |
| 正文 `--font-body` | Noto Sans SC | 400/500/600/700 | 一切 UI 文字 |

- Google Fonts CDN 引入(base.html);离线时回退系统字体栈,不影响功能。
- 数字展示用 `font-variant-numeric: tabular-nums`(统计、种族值、分页)。
- 标题字号梯度:hero 3.4rem → 页面 2rem → 区块 1.9rem/1.25rem → 卡片 1.05rem。

---

## 3. 组件规范

### 3.1 导航栏 `.navbar`
- 64px 固定顶栏,白卡面 + 底部发丝线;左:logo 星标(`.nav-logo`,紫渐变圆角方块)+ 衬线站名。
- 链接为 pill:常态次要文字,hover 浅底,激活 `.active` = `--color-primary-soft` 底 + 深色字 + 600 重。激活态由模板判断:`{% if '/pets/' in request.path %}active{% endif %}`(⚠️ Django 模板不支持 `.startswith` 带参,用 `in`)。
- 右侧 `.nav-actions`:主题切换 `.theme-toggle`(日/月 SVG 自动切换)、移动端汉堡 `.nav-toggle`(≤900px 显示,`body.nav-open` 展开下拉面板)。
- 禁止在 480px 下隐藏导航——这是历史硬伤,已修复,不得回退。

### 3.2 按钮 `.btn`
- `.btn-primary`:紫底白字 + 紫光投影,主行动一个页面/区块只放一个。
- `.btn-secondary`:卡面 + 发丝描边,hover 描边变紫。
- `.btn-danger`:错误色。`.btn-sm`:小号。
- 所有按钮 `active` 时 `scale(.97)`;hero 里的按钮用 `.btn` 且宽度自适应(`.hero-cta .btn { width:auto }`)。

### 3.3 卡片 `.card` / `.tool-card` / `.news-card` / `.stat-card`
- 统一配方:`--color-card` 底 + 1px `--color-border` + `--radius-lg` + `--shadow-sm`。
- hover 统一三段:上浮 -3px + 描边变紫(45% 透明度)+ `--shadow-lg` 加 1px 紫光晕。
- 图鉴卡图片区:同色相高明度渐变底(浅色 `#F6F6FA→#EEECFE`,暗色 `#1E2029→#2A2650`),立绘 hover 微放大 1.04。
- 工具卡图标盒 `.tool-icon` + 色阶 `.ti-violet/blue/teal/orange/rose/gold`(同族两色 135° 渐变),内嵌白色 2px 描边 SVG,**禁止 emoji 当图标**。

### 3.4 属性徽章 `.element-badge`
- pill 形,底色 `var(--element-XX)` 内联指定,白字 600 重 + 14px 属性图标。
- 属性筛选钮 `.element-icon`:38px 圆形、`--input-bg` 底;选中 `.active` = 2px 属性色描边 + 卡面底 + primary-soft 外环。

### 3.5 筛选栏 `.filter-bar`
- 卡片化(同 3.3 配方)+ 内部行距 12px。
- `.search-input`:无边框浅底,聚焦时变白底 + 紫描边 + 3px primary-soft 光环。
- `.cat-btn` pill:激活 = 紫底白字 + 紫光投影。

### 3.6 Toast `.messages .message`
- 右下浮层,卡片面 + 左侧 4px 语义色条 + `--shadow-lg`,3.6s 自动淡出(base.html 统一处理)。

### 3.7 页脚 `.footer-v2`
- 三段式:品牌区(logo+简介)/ 链接组(工具、支持)/ 底部版权栏,之间发丝线分隔;移动端纵向堆叠。

### 3.8 其他
- `.pagination`:激活页紫底 + 紫光投影;`.tabs`:下划线式,激活紫色 600;`.skill-table`:表头浅底,行 hover 浅底;`.stat-fill-*`:六维双色渐变条,入场生长动画。

---

## 4. 交互规范

| 场景 | 规范 |
|---|---|
| HTMX 请求 | 顶部 2px 渐变进度条(`#htmx-progress`,紫→金),`body.htmx-request` 触发;目标容器请求中降透明 0.55 |
| 内容入场 | 卡片类 `fadeUp 0.35s ease both`(HTMX 局部刷新后自然重播) |
| 加载骨架 | `.skeleton` 流光占位(shimmer 1.2s),供列表筛选接入 |
| 种族值条 | `statGrow 0.8s` 生长 + `cubic-bezier(.22,1,.36,1)` 缓出 |
| 快捷键 | `/` 聚焦页面搜索框(base.html 统一绑定) |
| 主题切换 | localStorage `roco-theme` + 系统偏好跟随;CSS 加载前内联脚本写入,杜绝闪烁 |
| 动效降级 | `prefers-reduced-motion: reduce` 全局关闭动画(已内置,新增动画无需再写) |
| 焦点 | `:focus-visible` 2px 紫色描边,键盘可达 |

---

## 5. 页面模式

### 首页(2026-07-26 已落地,作为基准)
Hero(徽章 pill + 双行衬线大标题 + 双 CTA + 紫渐变立绘面板·浮动徽章·热门卡)→ 四格数据统计条(数字走视图动态统计)→ 工具矩阵(3×2 bento)→ 最新资讯(静态三卡,封面图缺失时按分类渐变 `.nc-*` 兜底)→ 三段式页脚。

### 列表页(图鉴/技能)
页面头(衬线标题 + 副文案)→ 筛选栏卡片(搜索 + 属性图标行 + 形态 pill)→ 卡片网格 → 分页。骨架屏用于筛选/搜索的 HTMX 刷新间隙。

### 详情页
区块卡 `.detail-section` 堆叠,标题带 2px primary-soft 下划;主视觉图配同色相渐变底;进化链圆节点 + 当前节点紫光晕。

### 工具页(PVP/克制/孵蛋,待优化)
保持"一个页面一个主行动";对战区可用大面积紫渐变面板呼应首页 hero;输入控件全部走 `.form-group` + 聚焦光环规范。

---

## 6. 工程注意事项

1. **样式只改 `static/css/style.css` 与页面 `extra_head` 块**,模板类名 API 保持稳定,禁止重命名既有类。
2. **缓存控制(重要)**:`base.html` 中样式表带版本号 `style.css?v=YYYYMMDDxx`,**每次修改 `style.css` 后必须 bump 版本号**,否则用户浏览器会用旧缓存渲染(会出现渐变文字消失、圆角失效、新组件裸奔等"样式回退"症状)。
3. **页面级内联样式必须给 `var()` 写兜底值**,如 `var(--color-gold,#F0B53F)`、`var(--radius-lg,16px)`——即使命中旧缓存的全局 CSS,页面也能正常渲染。
4. Django 模板不支持 `.startswith` 带参调用,路径判断用 `{% if '/pets/' in request.path %}`。
5. 图标一律内联 SVG(白 2px 描边风格);文本节点禁用 emoji 图标。
6. 服务器:用 `D:\Anaconda\python.exe manage.py runserver`(不加 `--noreload`,模板/静态文件/Python 改动自动生效;若发现改了文件但页面不更新,先确认没有多个进程抢占 8000 端口,必要时杀掉重来)。
7. 新增页面先在 `extra_head` 写页面级样式,复用率高的再沉淀进 `style.css`。
