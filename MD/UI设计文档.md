# 洛克王国世界工具合集 · UI 设计文档

> 版本:v2(2026-07 全站改版)
> 适用范围:`static/css/style.css` 设计系统与全站模板
> 技术栈:原生 CSS(变量驱动)+ HTMX + 原生 JS,无前端框架

---

## 1. 设计方向

**轻游戏化**:以精致的工具站为底,叠加游戏氛围点缀。具体表现为——

- 紫金品牌配色(紫为主、金为点缀),呼应游戏世界观
- 衬线中文标题(Noto Serif SC)营造"图鉴/典籍"质感,正文用无衬线保证可读性
- 属性色、稀有度色等游戏数据色直接参与界面语义
- 卡片圆角、柔和阴影、悬停上浮、渐入动效,克制不花哨
- 完整的明暗双主题,所有组件双主题可用

---

## 2. 设计令牌(Design Tokens)

全部定义在 `style.css` 顶部 `:root`,暗色主题在 `[data-theme="dark"]` 中覆盖同名变量。**任何新组件都必须引用变量,禁止硬编码颜色**。

### 2.1 品牌色

| 变量 | 亮色值 | 用途 |
|------|--------|------|
| `--color-primary` | `#6D5DF6` | 主品牌紫,按钮/链接/选中态 |
| `--color-primary-dark` | `#5848D6` | 主色 hover/active |
| `--color-primary-soft` | `#EEECFE` | 主色浅底(选中背景、focus 光环) |
| `--color-gold` | `#F0B53F` | 金色点缀(kicker、本系标记、价格) |
| `--color-gold-soft` | `#FDF3DC` | 金色浅底 |

### 2.2 对战语义色(攻/防)

PVP 相关界面的红蓝语义,槽位选中、面板顶边、角色徽标、伤害结果统一使用:

| 变量 | 亮色值 | 用途 |
|------|--------|------|
| `--color-atk` / `--color-atk-soft` | `#F4536E` / `#FEEDF0` | 进攻方 |
| `--color-def` / `--color-def-soft` | `#4A8FF5` / `#EAF2FE` | 防守方 |

### 2.3 中性色

| 变量 | 亮色值 | 用途 |
|------|--------|------|
| `--color-bg` | `#F6F6FA` | 页面背景 |
| `--color-card` | `#FFFFFF` | 卡片背景 |
| `--color-card-inset` | `#F7F7FB` | 卡片内嵌套区块背景 |
| `--color-text` | `#22252F` | 主文字 |
| `--color-text-light` | `#6E7382` | 次要文字 |
| `--color-text-faint` | `#9BA0AE` | 弱化文字(占位/提示) |
| `--color-border` | `#E8E9F1` | 边框 |
| `--input-bg` | `#F1F2F8` | 输入框/图标底 |

### 2.4 状态与数据色

- 语义色:`--color-success #23A094`、`--color-error #F4536E`、`--color-warning #F59E0B`
- HP 条:`--hp-green / --hp-yellow / --hp-red`(伤害占比 <30% / <60% / ≥60%)
- 属性色:`--element-{属性名}` 共 18 个(普通/草/火/水/光/地/冰/龙/电/毒/虫/武/翼/萌/幽/恶/机械/幻),明暗主题通用
- 稀有度色:`--rarity-{白|绿|蓝|紫|金|橙}`,用于物品卡左边条与稀有度徽章

### 2.5 字体

```css
--font-display: "Noto Serif SC", "Songti SC", serif;   /* 标题/名称 */
--font-body: "Noto Sans SC", -apple-system, ..., sans-serif;  /* 正文/控件 */
```

- `h1-h3`、卡片标题、面板标题走 display 衬线;表单控件、按钮、正文走 body 无衬线
- 数字场景(种族值、价格、倒计时)加 `font-variant-numeric: tabular-nums` 保证等宽对齐

### 2.6 尺寸 / 圆角 / 阴影

- 容器:`--max-width 1200px`(常规页)、`--max-width-tool 1400px`(计算器宽页,模板加 `body_class: wide-page`)
- 导航高度:`--navbar-height 64px`
- 圆角四档:`--radius-sm 8` / `--radius 12` / `--radius-lg 16` / `--radius-pill 999`
- 阴影三档 + 光晕:`--shadow-sm / -md / -lg / --shadow-glow`

---

## 3. 明暗主题机制

- 主题属性挂在 `<html data-theme="light|dark">`,**不挂 body**——base.html `<head>` 内联脚本在 CSS 加载前执行,首屏无闪烁
- 优先级:`localStorage('roco-theme')` > 系统 `prefers-color-scheme`
- 切换按钮 `.theme-toggle` 位于导航右侧,点击写回 localStorage
- CSS 侧一律用 `[data-theme="dark"] .xxx` 覆盖;渐变类背景(卡片图底、hero)需要单独写暗色版本
- 新组件自测清单:亮色 ✓ 暗色 ✓ 明暗切换过渡自然 ✓

---

## 4. 布局与响应式

三个断点,移动优先降级:

| 断点 | 行为 |
|------|------|
| `≤900px` | 导航折叠为汉堡菜单;伤害结果/PVP 双栏变单栏;PVP 槽位列变 6 列横排,顺序调整为 己方→敌方→配置 |
| `≤768px` | 卡片网格缩小最小列宽;精灵详情图文改纵向;品牌文字隐藏;面板值卡变单列 |
| `≤480px` | 卡片网格固定 2 列;标题字号下调 |

页面骨架:`navbar(fixed) → main.container → footer`。计算器类页面通过 `{% block body_class %}wide-page{% endblock %}` 获得 1400px 宽容器。

---

## 5. 组件库

### 5.1 通用组件

| 组件 | 类名 | 说明 |
|------|------|------|
| 按钮 | `.btn` + `-primary/-secondary/-ghost/-danger`,尺寸 `-sm/-xs`,通栏 `-block` | primary 带品牌色阴影;active 缩放反馈 |
| 卡片 | `.card` `.card-img` `.card-body` | 悬停上浮 + 品牌色描边;图底渐变分明暗 |
| 卡片网格 | `.card-grid` `.card-grid-4` | auto-fill 自适应列 |
| 属性徽章 | `.element-badge` | 背景取 `--element-*`,含小图标 |
| 属性图标选择器 | `.element-grid` `.element-icon(.active)` | 38px 圆形,选中描边取 `--element-current` |
| 筛选栏 | `.filter-bar` `.filter-row` `.search-input` `.filter-label` | 页面顶部统一筛选容器 |
| 分类按钮 | `.cat-btn(.active)` | 胶囊形,选中实心紫 |
| 种族值条 | `.stat-list` `.stat-item` `.stat-fill-{hp/pa/ma/pd/md/sp}` | 六维彩色渐变,入场生长动画 |
| 标签页 | `.tabs` `.tab-nav` `.tab-btn` `.tab-panel` | 下划线式 |
| 表格 | `.skill-table` + `.table-scroll` | 移动端横向滚动包裹 |
| 表单 | `.form-group` | 输入/下拉/文本域统一 focus 光环 |
| 分页 | `.pagination` | 列表页多用 HTMX `revealed` 无限滚动替代 |
| Toast | `.messages .message(-success/-error/-warning)` | 右下角浮出,自动淡出;JS 用 `rocoToast(text, type)`,**禁止 alert()** |
| 空状态 | `.empty-state` `.panel-empty` `.tier-none` | 居中弱化文案 |
| 骨架屏/进度 | `.skeleton`、`#htmx-progress` | HTMX 请求顶部渐变进度条,目标区域降透明度 |

### 5.2 工具页组件(PVP/伤害计算器等)

| 组件 | 类名 | 说明 |
|------|------|------|
| 工具页头 | `.tool-header` + `.step-hints .step .step-num` | 居中标题 + 三步操作引导 |
| 面板 | `.panel(-atk/-def)` `.panel-title` | 攻红/防蓝顶边与标题色 |
| 角色徽标 | `.role-dot(-atk/-def)` | 「攻」「防」方形小徽章 |
| 阵容槽位 | `.slot(.has/.sel-atk/.sel-def)` `.slot-pos` `.slot-name` `.slot-role` `.slot-actions` | 空位虚线+号;选中攻/防彩色描边+角标;悬停底部 22px 细操作栏(换/✕),触屏(`hover:none`)自动隐藏 |
| 精灵选择弹窗 | `.picker-overlay(.on)` `.picker` `.picker-head` `.picker-elems` `.picker-body` `.picker-item` | 磨砂遮罩;头部搜索 + 属性图标筛选行;Enter 选首项、Esc 关闭 |
| 已选精灵行 | `.picked-pet` `.pp-actions` | 面板内精灵信息 + 常驻「更换/移除」按钮(触屏主入口) |
| 数值调节组 | `.adjust-group` `.adjust-title` `.adjust-row` `.num-input` `.select-input` | 强化层数/全局加成等紧凑数字输入 |
| 面板值卡 | `.statcard` `.statcard-grid` `.stat-cell(.st-value.boosted)` `.nature-row` | 六维面板 + 天分输入 + 性格选择 |
| 技能面板 | `.skills-panel` `.skill-slot-row` | 4 个技能下拉 + 单技能威力/连击微调 |
| 伤害结果 | `.dmg-results` `.dmg-panel(.atk/.def)` `.dmg-row` `.dmg-value(.lethal)` `.hp-track .hp-fill` | 双栏攻防结果;斩杀伤害红色;HP 条三色 |
| 联想下拉 | `.suggest-anchor` `.suggest-box(.active)` `.suggest-filter` `.suggest-pet` `.suggest-chip` | 搜索框下挂;属性图标筛选行 |
| 上传区 | `.upload-zone(.dragover)` `.upload-preview` | 截图识别拖拽上传 |
| 折叠卡 | `.acc-card(.open)` `.acc-head` `.acc-body` | 识别结果逐精灵展开 |

### 5.3 物品图鉴组件

| 组件 | 类名 | 说明 |
|------|------|------|
| 物品卡 | `.item-card` + `.rarity-border-{稀有度}` | 左侧 3px 稀有度色条;整卡可点(`role="button"`)打开详情 |
| 图标底 | `.item-icon-wrap` | 56px 内嵌底;缺图 `onerror` 隐藏 |
| 稀有度徽章 | `.rarity-badge.rarity-{白绿蓝紫金橙}` | 实心色胶囊 |
| 分类标签 | `.item-cat-tag` | 灰底胶囊 |
| 详情弹窗 | 复用 `.picker-*` + `.im-head/.im-icon/.im-name/.im-section/.im-label` | HTMX 拉取 `/items/<id>/detail/`;用途/描述/获取途径分段 |

### 5.4 首页商人展台

hero 右侧紫色渐变面板整体为「远行商人」展台(`.merchant-visual .mv-*`):

- 头部:标题 + 当日轮次 + 白色胶囊倒计时(`.mc-countdown`,JS 每秒刷新,归零后随机延迟 3-8s 刷新页面)
- 商品:`≤4 件` 用 2×2 大格(`.mv-items`);`>4 件`(周末,上限 8)用上 4 下余、两排居中的紧凑格(`.mv-rows .mv-row`)
- 商品格 `.mv-item`:图标/名称/金色价格/限购,统一模板 `core/_merchant_item.html`
- 空态两种:休息中(💤 赶路文案)/未收录(配置提示),均带虚线框

---

## 6. 交互规范

- **反馈**:所有异步操作有可见反馈——HTMX 顶部进度条、目标区域变淡、toast 结果提示;禁止无反馈的静默失败与原生 `alert()`
- **键盘**:`/` 聚焦页面搜索框;弹窗内 Esc 关闭、Enter 选首项;物品卡 Tab 聚焦后 Enter 打开详情
- **悬停操作不挡主操作**:槽位的换/删收在底部细条,主体区域留给最常用的点击;触屏设备操作入口改为面板常驻按钮
- **加载策略**:列表用 HTMX `revealed` 无限滚动;图片 `loading="lazy"`;缺图优雅降级(隐藏或 🎁 占位)
- **动效克制**:入场 fadeUp/popIn ≤0.35s;`prefers-reduced-motion` 下全部禁用

---

## 7. 页面索引

| 页面 | 模板 | 主要组件 |
|------|------|----------|
| 首页 | `core/home.html` | hero + 商人展台、统计条、工具矩阵、资讯卡 |
| 精灵图鉴/详情 | `pets/pet_list|pet_detail` | 筛选栏、卡片网格、种族值条、进化链、克制分组、技能表 |
| 技能图鉴/详情 | `pets/skill_list|skill_detail` | 同上 + 分类按钮 |
| 物品图鉴 | `items/item_list` | 物品卡、稀有度筛选、详情弹窗 |
| 克制计算器 | `pets/type_calc` | 属性图标选择器、克制分组 |
| PVP 计算器 | `pvp/battle_calc` | 槽位列、攻防面板、选精灵弹窗、伤害结果 |
| 伤害计算器 | `pvp/damage_calc` | 攻防面板、联想下拉、面板值卡、技能面板、伤害结果 |
| 截图识别 | `pvp/capture|capture_result` | 上传区、折叠卡 |
| 孵蛋查询 | `eggs/hatch_lookup` | 筛选栏表单、卡片网格 |
| 资讯 | `articles/*` | 文章卡、正文容器 |
| 登录/注册 | `accounts/*` | auth 卡片 |

---

## 8. 维护约定

1. **改 `style.css` 必须递增 base.html 里的版本号**(`?v=YYYYMMDD[a-z]`),否则用户浏览器用旧缓存
2. 可复用样式进 `style.css` 对应分区;仅单页使用的样式放该页 `{% block extra_head %}`,且同样只用变量
3. 新增属性/稀有度:在 `:root` 加 `--element-*` / `--rarity-*` 变量即可,组件自动生效
4. 新组件必须:引用设计令牌、通过明暗双主题检查、≤900px 断点可用
5. 开发模式已关闭模板缓存(settings.py),改模板刷新即生效;改 CSS 记得第 1 条
6. 局部模板复用:商品格 `core/_merchant_item.html`、物品卡 `items/item_card.html`,改样式只动一处
