"""
S10 — 实时屏幕捕获 + 精灵识别流水线

串联 S1（头像提取）+ S3（匹配）为端到端流程：
  屏幕捕获 → 橙色面板检测 → 卡片检测 → 头像裁剪 → 颜色匹配 → 输出阵容

用法：
  python pvp_assistant/realtime_capture.py                          # 实时捕获全屏
  python pvp_assistant/realtime_capture.py <截图路径>                # 调试：处理截图文件
  python pvp_assistant/realtime_capture.py --roi x1,y1,x2,y2        # 指定 ROI 区域
  python pvp_assistant/realtime_capture.py --calibrate              # 校准模式：截图存盘，手动量坐标
"""

import cv2
import numpy as np
from PIL import ImageGrab
from pathlib import Path
import sys
import time
import json

# 把 pvp_assistant 加到路径，复用已有模块
sys.path.insert(0, str(Path(__file__).resolve().parent))

ROI_CONFIG = Path(__file__).resolve().parent / "roi_config.json"
DEBUG_DIR = Path(r"D:\Project\LuoKeWangGuo\MD\DEBUG")


def imwrite_unicode(path, img):
    """安全写入，支持中文路径。"""
    ext = Path(path).suffix
    success, buf = cv2.imencode(ext, img)
    if success:
        buf.tofile(str(path))
import sys
import time

# 把 pvp_assistant 加到路径，复用已有模块
sys.path.insert(0, str(Path(__file__).resolve().parent))

# ── S1: 头像提取（内联，避免文件 I/O） ──

def detect_orange_region(bgr):
    """检测对手面板的橙色背景区域。通过形状而非位置识别。"""
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    lower = np.array([3, 40, 40])
    upper = np.array([28, 255, 255])
    mask = cv2.inRange(hsv, lower, upper)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None

    # PVP 面板特征：大（>50000px）且接近正方形（0.7~1.4），过滤掉桌面横条
    candidates = []
    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        aspect = w / h if h > 0 else 0
        if w * h > 50000 and 0.7 < aspect < 1.4:
            candidates.append((w * h, (x, y, w, h)))

    if candidates:
        candidates.sort(reverse=True)
        return candidates[0][1]

    return None


def detect_dark_cards(gray_panel):
    """检测深色卡片矩形。"""
    panel_h, _ = gray_panel.shape[:2]
    _, mask = cv2.threshold(gray_panel, 80, 255, cv2.THRESH_BINARY_INV)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((7, 7), np.uint8))
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    min_h, max_h = int(panel_h * 0.05), int(panel_h * 0.12)
    top_exclude = int(panel_h * 0.12)

    cards = []
    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        if not (min_h <= h <= max_h): continue
        if y < top_exclude: continue
        if not (3 < w / h < 15): continue
        if w * h < panel_h * 10: continue
        cards.append((x, y, w, h))

    cards.sort(key=lambda r: r[1])
    return cards[:6]


def extract_avatars(panel, cards):
    """从卡片中提取 6 个头像区域。"""
    max_cw = max(c[2] for c in cards)
    avatars = []
    for cx, cy, cw, ch in cards:
        card_right = cx + cw + (max_cw - cw)  # 归一化补偿
        av_size = ch
        ax = max(0, card_right - av_size - 2)
        ay = max(0, cy)
        av_size = min(av_size, panel.shape[1] - ax, panel.shape[0] - ay)
        avatars.append(panel[ay:ay + av_size, ax:ax + av_size])
    return avatars


# ── S3: 颜色匹配 ──

GRID, BINS = 4, 32

def load_library():
    """加载 BWIKI 头像库。"""
    lib_dir = Path(r"D:\Project\LuoKeWangGuo\static\images\pets_head")
    library = {}
    for f in lib_dir.glob("*.png"):
        data = np.fromfile(str(f), dtype=np.uint8)
        img = cv2.imdecode(data, cv2.IMREAD_COLOR)
        if img is not None:
            library[f.stem] = img
    return library


def compute_hist(img):
    """4×4 网格颜色直方图。"""
    h, w = img.shape[:2]
    cell_h, cell_w = h // GRID, w // GRID
    all_hists = []
    for row in range(GRID):
        for col in range(GRID):
            cell = img[row*cell_h:(row+1)*cell_h, col*cell_w:(col+1)*cell_w]
            gray = cv2.cvtColor(cell, cv2.COLOR_BGR2GRAY)
            mask = (gray > 40).astype(np.uint8)
            hist = cv2.calcHist([cell], [0,1,2], mask, [BINS]*3, [0,256]*3)
            all_hists.append(cv2.normalize(hist, hist).flatten())
    return np.concatenate(all_hists)


def match_avatar(avatar, library):
    """匹配单张头像。"""
    avatar = cv2.flip(avatar, 1)  # 朝右对齐 BWIKI
    th, tw = avatar.shape[:2] if avatar.shape[0] > 0 else avatar.shape[:2] if 0 else (80, 80)
    t_hist = compute_hist(avatar)
    
    scores = []
    for name, lib_img in library.items():
        lib_r = cv2.resize(lib_img, (avatar.shape[1], avatar.shape[0]), interpolation=cv2.INTER_AREA)
        l_hist = compute_hist(lib_r)
        score = cv2.compareHist(t_hist, l_hist, cv2.HISTCMP_CORREL)
        scores.append((name, score))
    
    scores.sort(key=lambda x: x[1], reverse=True)
    return scores[0], scores[1] if len(scores) > 1 else None


# ── 主流程 ──

def load_roi():
    """从配置文件加载 ROI。"""
    if ROI_CONFIG.exists():
        data = json.loads(ROI_CONFIG.read_text(encoding="utf-8"))
        left, top, right, bottom = data["roi"]
        return left, top, right, bottom
    return None


def save_roi(left, top, right, bottom):
    """保存 ROI 到配置文件。"""
    ROI_CONFIG.write_text(
        json.dumps({"roi": [left, top, right, bottom]}, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def calibrate():
    """校准模式：截屏，拖动框选游戏窗口区域，保存 ROI 配置。"""
    print("截取桌面中...")
    img = ImageGrab.grab()
    bgr = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

    print("\n请在弹出的窗口中拖动鼠标框选游戏窗口区域")
    print("按 Enter 确认，按 Esc 取消\n")

    roi = cv2.selectROI("拖动框选游戏窗口 → Enter确认", bgr, False)
    cv2.destroyAllWindows()

    x, y, w, h = roi
    if w == 0 or h == 0:
        print("未选择区域，取消。")
        return

    left, top, right, bottom = x, y, x + w, y + h
    save_roi(left, top, right, bottom)
    print(f"\nROI 已保存: ({left},{top}) → ({right},{bottom})")
    print(f"区域大小: {w}x{h}")
    print(f"\n现在直接运行脚本即可：")
    print(f"  venv\\Scripts\\python.exe pvp_assistant\\realtime_capture.py")


def main():
    # ── 参数解析 ──
    if len(sys.argv) > 1:
        if sys.argv[1] == "--calibrate":
            calibrate()
            return
        elif sys.argv[1] == "--roi" and len(sys.argv) > 2:
            parts = sys.argv[2].split(",")
            if len(parts) == 4:
                left, top, right, bottom = map(int, parts)
                save_roi(left, top, right, bottom)
                print(f"ROI 已保存: left={left}, top={top}, right={right}, bottom={bottom}")
                print(f"现在直接运行脚本即可使用此 ROI：")
                print(f"  venv\\Scripts\\python.exe pvp_assistant\\realtime_capture.py")
                return

    debug_screenshot = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else None

    print("=" * 55)
    print("  洛克王国 PVP 实时精灵识别")
    if debug_screenshot:
        print(f"  [调试模式] 文件: {Path(debug_screenshot).name}")
    print("=" * 55)

    # 1. 加载头像库
    print("\n[1/3] Loading BWIKI library...")
    library = load_library()
    print(f"      {len(library)} avatars loaded")

    # ROI 配置
    roi = load_roi()
    if roi:
        print(f"      ROI: ({roi[0]},{roi[1]}) → ({roi[2]},{roi[3]})")

    if debug_screenshot:
        filepath = Path(debug_screenshot)
        if not filepath.exists():
            print(f"      ERROR: File not found: {filepath}")
            return
        data = np.fromfile(str(filepath), dtype=np.uint8)
        frame = cv2.imdecode(data, cv2.IMREAD_COLOR)
        if frame is None:
            print(f"      ERROR: Cannot read image: {filepath}")
            return
        process_and_show(frame, library)
        return

    # ── 实时模式 ──
    print("\n[2/3] Initializing screen capture (PIL)...")
    if roi:
        print(f"      ROI: ({roi[0]},{roi[1]}) → ({roi[2]},{roi[3]})")
    print("      Ready")

    if not roi:
        print("\n[!] 未配置 ROI，将捕获整个桌面。")
        print("    如果桌面有其他橙色窗口可能干扰识别。")
        print("    运行 --calibrate 设置游戏窗口区域：")
        print(f"      venv\\Scripts\\python.exe pvp_assistant\\realtime_capture.py --calibrate")

    print("\n[3/3] 等待按键...")
    print("      ┌─────────────────────────────────────────┐")
    print("      │  F12 = 捕获并识别敌方阵容              │")
    print("      │  Esc = 退出                            │")
    print("      └─────────────────────────────────────────┘")

    import msvcrt
    count = 0
    while True:
        if msvcrt.kbhit():
            key = msvcrt.getch()
            if key == b'\x1b':
                print("\n      退出。")
                break
            elif key in (b'\x00', b'\xe0'):
                key2 = msvcrt.getch()
                if key2 == b'\x86':
                    count += 1
                    print(f"\n      [#{count}] F12 按下，捕获中...")
                    img = ImageGrab.grab(bbox=roi)  # RGB PIL Image
                    bgr = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
                    process_and_show(bgr, library, count)
                    print("\n      等待下一次按键...")
        time.sleep(0.05)


def process_and_show(bgr, library, capture_count=0):
    """检测 + 提取 + 匹配：处理一帧并打印结果。"""
    orange = detect_orange_region(bgr)
    if orange is None:
        print("      ERROR: 未检测到橙色面板！请确认 PVP 界面可见。")
        return
    ox, oy, ow, oh = orange

    if ow < 300 or oh < 300:
        print("      ERROR: 检测到的橙色区域太小，不是游戏面板。")
        return

    panel = bgr[oy:oy + oh, ox:ox + ow]
    gray_panel = cv2.cvtColor(panel, cv2.COLOR_BGR2GRAY)

    cards = detect_dark_cards(gray_panel)
    print(f"      检测到 {len(cards)} 张卡片")

    # ── 生成调试图片（无论检测到几张都生成，方便排查） ──
    DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    debug_img = bgr.copy()
    cv2.rectangle(debug_img, (ox, oy), (ox + ow, oy + oh), (0, 165, 255), 3)

    if cards:
        max_cw_local = max(c[2] for c in cards)
        for i, (cx, cy, cw, ch) in enumerate(cards):
            abs_x, abs_y = ox + cx, oy + cy
            cv2.rectangle(debug_img, (abs_x, abs_y), (abs_x + cw, abs_y + ch), (0, 255, 0), 2)
            av_size = ch
            compensated_right = abs_x + max_cw_local
            ax = compensated_right - av_size - 2
            cv2.rectangle(debug_img, (ax, abs_y), (ax + av_size, abs_y + av_size), (255, 0, 0), 2)
            cv2.putText(debug_img, f"#{i + 1}", (ax - 30, abs_y + 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

    debug_path = DEBUG_DIR / f"debug_{timestamp}.png"
    imwrite_unicode(str(debug_path), debug_img)
    print(f"      调试图: MD/DEBUG/debug_{timestamp}.png")

    if len(cards) < 4:
        print("      ERROR: 卡片不足 4 张！请确认 PVP 战斗画面可见。")
        return

    avatars = extract_avatars(panel, cards)

    # 识别结果
    results = []
    for av in avatars:
        if av is None or av.size == 0:
            results.append(("(空)", 0, 0))
            continue
        (name, score), second = match_avatar(av, library)
        gap = score - second[1] if second else 0
        results.append((name, score, gap))

    print("\n      ┌──────── 敌方阵容 ────────┐")
    for i, (name, score, gap) in enumerate(results):
        print(f"      │ #{i+1}: {name:<12} {score:.3f} (+{gap:.3f}){'':<2}│")
    print("      └──────────────────────────┘")


if __name__ == "__main__":
    main()
