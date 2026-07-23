"""
从游戏截图中提取对手6个精灵的头像。

策略：
1. HSV 色域检测橙色背景 → 确定对手面板区域
2. 对手面板内用深色阈值找卡片轮廓 → 定位6张精灵卡片
3. 从每张卡片右端裁剪圆形头像
"""

import cv2
import numpy as np
from pathlib import Path
import sys


def imread_unicode(path):
    """OpenCV imread 不支持中文路径，用 numpy 绕过"""
    data = np.fromfile(str(path), dtype=np.uint8)
    return cv2.imdecode(data, cv2.IMREAD_COLOR)


def imwrite_unicode(path, img):
    """OpenCV imwrite 不支持中文路径"""
    ext = Path(path).suffix
    success, buf = cv2.imencode(ext, img)
    if success:
        buf.tofile(str(path))
    return success

# ── 项目根目录 ──────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
GAME_AVATARS_DIR = Path(__file__).resolve().parent / "game_avatars"
SCREENSHOT_PATH = BASE_DIR / "MD" / "游戏机制" / "屏幕截图 2026-06-24 152236.png"


def detect_orange_region(hsv):
    """
    检测对手面板的橙色背景区域。
    返回 (x, y, w, h) 或 None。
    """
    # 橙色在 HSV 空间：H 约 5-25, S 中等, V 偏亮
    # 先用宽阈值
    lower = np.array([3, 40, 40])
    upper = np.array([28, 255, 255])
    mask = cv2.inRange(hsv, lower, upper)

    # 形态学闭操作：合并近邻区域
    kernel = np.ones((15, 15), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None

    # 最大的橙色轮廓 = 对手面板
    best = max(contours, key=cv2.contourArea)
    return cv2.boundingRect(best)


def detect_dark_cards(gray_panel):
    """
    在对手面板灰度图中检测深色矩形卡片。
    返回按 y 坐标排序的卡片矩形列表 [(x, y, w, h), ...]。
    """
    panel_h, panel_w = gray_panel.shape[:2]

    # 深色卡片：像素值较低的暗色区域
    _, mask = cv2.threshold(gray_panel, 80, 255, cv2.THRESH_BINARY_INV)

    # 形态学操作：填小洞、合并碎片
    kernel = np.ones((7, 7), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # 筛选：面积 + 宽高比 + 高度范围 + Y位置（避开顶部UI）
    min_area = panel_h * 10
    min_card_h = int(panel_h * 0.05)  # 最小高度 ~5% 面板高度
    max_card_h = int(panel_h * 0.12)  # 最大高度 ~12% 面板高度
    top_ui_exclude = int(panel_h * 0.12)  # 排除顶部 12% 区域

    cards = []
    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        area = w * h

        # 高度检查
        if not (min_card_h <= h <= max_card_h):
            continue

        # Y位置检查：避开顶部UI区域
        if y < top_ui_exclude:
            continue

        # 宽高比检查（扁长条卡片）
        if not (3 < w / h < 15):
            continue

        # 面积检查
        if area < min_area:
            continue

        cards.append((x, y, w, h))

    # 按 y 坐标从上到下排序
    cards.sort(key=lambda r: r[1])
    return cards


def extract_avatar(panel_img, card_rect, max_card_width):
    """
    从卡片矩形中截取右侧头像区域。

    核心问题：不同卡片的暗色检测宽度不一致（244-296px），
    窄卡片在头像区域前截断，导致提取偏左。

    解决方案：用最大卡片宽度归一化右边界，
    使所有卡片头像提取基于同一水平基准。
    """
    cx, cy, cw, ch = card_rect
    panel_h, panel_w = panel_img.shape[:2]

    # 用最大卡片宽度补偿窄卡片的暗色截断
    compensated_right = cx + max_card_width

    # 头像至少需要卡片高度这么大的正方形
    avatar_size = ch

    # 从补偿后的右边缘向左提取
    ax = compensated_right - avatar_size - 2
    ay = cy

    # 边界保护
    ax = max(0, ax)
    ay = max(0, ay)
    avatar_size = min(avatar_size, panel_w - ax, panel_h - ay)

    avatar = panel_img[ay:ay + avatar_size, ax:ax + avatar_size]
    return avatar


def save_debug_image(img, panel_bgr, cards, avatars, output_path):
    """生成调试图片：标出橙色区域、卡片框、头像框"""
    debug = img.copy()
    h, w = debug.shape[:2]

    # 画橙色区域框
    ox, oy, ow, oh = detect_orange_region(cv2.cvtColor(img, cv2.COLOR_BGR2HSV))
    if ox is not None:
        cv2.rectangle(debug, (ox, oy), (ox + ow, oy + oh), (0, 165, 255), 3)

        # 画卡片框和头像框
        max_cw_local = max(c[2] for c in cards)
        for i, (cx, cy, cw, ch) in enumerate(cards):
            abs_x = ox + cx
            abs_y = oy + cy
            cv2.rectangle(debug, (abs_x, abs_y), (abs_x + cw, abs_y + ch), (0, 255, 0), 2)

            # 画头像框
            avatar_size = ch
            compensated_right = abs_x + max_cw_local
            ax = compensated_right - avatar_size - 2
            ay = abs_y
            cv2.rectangle(debug, (ax, ay), (ax + avatar_size, ay + avatar_size), (255, 0, 0), 2)
            cv2.putText(debug, f"#{i + 1}", (ax - 30, ay + 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

    imwrite_unicode(str(output_path), debug)
    print(f"  Debug image saved: {output_path}")


def main():
    # 支持命令行参数指定截图路径
    if len(sys.argv) > 1:
        screenshot = Path(sys.argv[1])
    else:
        screenshot = SCREENSHOT_PATH

    if not screenshot.exists():
        print(f"ERROR: Screenshot not found: {screenshot}")
        # 尝试查找任意截图
        screenshots = list(screenshot.parent.glob("*.png"))
        if screenshots:
            screenshot = screenshots[0]
            print(f"Using: {screenshot}")
        else:
            sys.exit(1)

    print(f"Loading: {screenshot.name}")
    img = imread_unicode(str(screenshot))
    if img is None:
        print("ERROR: Cannot read image")
        sys.exit(1)

    h, w = img.shape[:2]
    print(f"Image size: {w}x{h}")

    # ── 第1步：橙色区域检测 ──
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    orange_rect = detect_orange_region(hsv)
    if orange_rect is None:
        print("ERROR: Cannot detect orange background region")
        sys.exit(1)

    ox, oy, ow, oh = orange_rect
    print(f"Orange region: x={ox}, y={oy}, w={ow}, h={oh}")

    # 裁剪对手面板
    opponent_panel = img[oy:oy + oh, ox:ox + ow]
    gray_panel = cv2.cvtColor(opponent_panel, cv2.COLOR_BGR2GRAY)

    # ── 第2步：检测深色卡片 ──
    cards = detect_dark_cards(gray_panel)
    print(f"Detected {len(cards)} dark cards")

    if len(cards) < 6:
        print("WARNING: Expected 6 cards, relaxing threshold...")
        # 尝试放宽阈值
        _, mask = cv2.threshold(gray_panel, 100, 255, cv2.THRESH_BINARY_INV)
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        all_cards = []
        for c in contours:
            x, y, w, h_ = cv2.boundingRect(c)
            area = w * h_
            if area > oh * 5 and 2 < w / h_ < 20:
                all_cards.append((x, y, w, h_))
        all_cards.sort(key=lambda r: r[1])
        cards_used = all_cards[:6]
        print(f"  Relaxed detection found {len(cards_used)} cards")
    else:
        cards_used = cards[:6]

    # ── 第3步：提取头像 ──
    GAME_AVATARS_DIR.mkdir(parents=True, exist_ok=True)
    avatars = []

    # 计算最大卡片宽度，用于补偿窄卡片
    max_card_width = max(c[2] for c in cards_used)

    for i, card in enumerate(cards_used):
        avatar = extract_avatar(opponent_panel, card, max_card_width)
        avatars.append(avatar)
        out_path = GAME_AVATARS_DIR / f"avatar_{i + 1:02d}.png"
        imwrite_unicode(str(out_path), avatar)
        print(f"  Saved: {out_path.name} ({avatar.shape[1]}x{avatar.shape[0]})")

    # ── 第4步：生成调试图片 ──
    debug_path = BASE_DIR / "MD" / "游戏机制" / "debug_extraction.png"
    save_debug_image(img, opponent_panel, cards_used, avatars, debug_path)

    print(f"\nDone! Extracted {len(avatars)} avatars to {GAME_AVATARS_DIR}")
    print(f"Debug image: {debug_path}")


if __name__ == "__main__":
    main()
