"""
S3 模板匹配 —— 游戏头像识别（网格颜色直方图版）。

原理：将图片切成 4×4 网格，每格单独计算颜色直方图后拼接。
      既保留颜色信息，又编码空间位置。

朝向处理：BWIKI 头像（朝右）与游戏截图（朝左）镜像相反。
          匹配时将游戏头像翻转（cv2.flip）以对齐方向，
          库本身不做任何修改。
"""

import cv2
import numpy as np
from pathlib import Path

GAME_AVATARS_DIR = Path(r"D:\Project\LuoKeWangGuo\pvp_assistant\game_avatars")
LIBRARY_DIR = Path(r"D:\Project\LuoKeWangGuo\static\images\pets_head")

HIST_BINS = 32             # 直方图分箱数（32 最优：区分度够又不至于过拟合）
CONFIDENCE_THRESHOLD = 0.15  # 低于此值标记低置信度（可能是炫彩/低质量图片）


def imread_unicode(path):
    data = np.fromfile(str(path), dtype=np.uint8)
    return cv2.imdecode(data, cv2.IMREAD_COLOR)


def load_library():
    library = {}
    for f in sorted(LIBRARY_DIR.glob("*.png")):
        img = imread_unicode(f)
        if img is not None:
            library[f.stem] = img
    return library


GRID_SIZE = 4  # 网格大小：将图片切成 GRID_SIZE × GRID_SIZE 格

def compute_hist(img):
    """
    网格颜色直方图 — 将图片切成 GRID×GRID 格，每格单独计算 3D 颜色直方图，
    然后拼接成一个大向量。这样既保留了颜色信息，又编码了空间位置。
    BWIKI 头像库已全部向左翻转（cv2.flip），与游戏截图朝向一致，无需运行时翻转。
    """
    h, w = img.shape[:2]
    cell_h, cell_w = h // GRID_SIZE, w // GRID_SIZE

    all_hists = []
    for row in range(GRID_SIZE):
        for col in range(GRID_SIZE):
            y1, y2 = row * cell_h, (row + 1) * cell_h
            x1, x2 = col * cell_w, (col + 1) * cell_w
            cell = img[y1:y2, x1:x2]

            gray = cv2.cvtColor(cell, cv2.COLOR_BGR2GRAY)
            mask = (gray > 40).astype(np.uint8)
            hist = cv2.calcHist(
                [cell], [0, 1, 2], mask,
                [HIST_BINS, HIST_BINS, HIST_BINS],
                [0, 256, 0, 256, 0, 256]
            )
            all_hists.append(cv2.normalize(hist, hist).flatten())

    return np.concatenate(all_hists)


def match_one(target_path, library):
    target = imread_unicode(target_path)
    if target is None:
        return None

    th, tw = target.shape[:2]

    # 游戏头像朝左，BWIKI库朝右 → 翻转游戏头像以对齐朝向
    target = cv2.flip(target, 1)

    t_hist = compute_hist(target)

    results = []
    for name, lib_img in library.items():
        lib_r = cv2.resize(lib_img, (tw, th), interpolation=cv2.INTER_AREA)
        l_hist = compute_hist(lib_r)
        score = cv2.compareHist(t_hist, l_hist, cv2.HISTCMP_CORREL)
        results.append((name, score))

    results.sort(key=lambda x: x[1], reverse=True)

    best_name, best_score = results[0]
    warning = None
    if best_score < CONFIDENCE_THRESHOLD:
        warning = f"低置信度 ({best_score:.3f})，可能是炫彩或未收录精灵"

    return {
        "file": target_path.name,
        "size": f"{tw}x{th}",
        "best": best_name,
        "score": best_score,
        "warning": warning,
        "top3": results[:3],
    }


def main():
    library = load_library()
    lib_count = len(library)

    print("=" * 55)
    print("  S3 精灵头像识别 — 颜色直方图匹配")
    print("=" * 55)
    print(f"  库: {LIBRARY_DIR} ({lib_count} 只)")
    print(f"  输入: {GAME_AVATARS_DIR}")
    print(f"  方法: 4×4 网格 HSV 直方图 ({GRID_SIZE}²×{HIST_BINS}³ = {GRID_SIZE*GRID_SIZE*HIST_BINS**3} 维向量)")
    print(f"  警告阈值: score < {CONFIDENCE_THRESHOLD}")
    print("=" * 55)
    print()

    # 收集游戏头像（跳过调试文件）
    skip_prefixes = ("ref_", "method", "card_", "strip_", "debug")
    game_files = sorted(
        f for f in GAME_AVATARS_DIR.glob("*.png")
        if not any(f.stem.startswith(p) for p in skip_prefixes)
    )

    if not game_files:
        print("ERROR: 没有找到游戏头像！")
        print(f"请将命名的头像（如 化蝶.png）放入 {GAME_AVATARS_DIR}")
        return

    results = []
    for gf in game_files:
        result = match_one(gf, library)
        if result is None:
            continue
        results.append(result)

        flag = "⚠️" if result["warning"] else "  "
        print(f"  [{flag}] {result['file']} ({result['size']})")
        print(f"       → {result['best']}  得分: {result['score']:.3f}")
        if result["warning"]:
            print(f"       {result['warning']}")
        top3_str = ", ".join(f"{n} ({s:.3f})" for n, s in result["top3"])
        print(f"       Top 3: {top3_str}")
        print()

    # 汇总
    matched = sum(1 for r in results if not r["warning"])
    warned = sum(1 for r in results if r["warning"])
    print(f"--- 共 {len(results)} 张，准确 {matched}，警告 {warned} ---")


if __name__ == "__main__":
    main()
