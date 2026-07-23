"""
截图识别流水线：上传图片 → 橙色面板检测 → 卡片裁剪 → 头像匹配 → 精灵名单。

依赖: cv2, numpy, realtime_capture.py（同目录下的检测/匹配函数）
"""

import cv2
import numpy as np
from pathlib import Path
import sys

# 同目录导入
_pkg = Path(__file__).resolve().parent
sys.path.insert(0, str(_pkg))

from realtime_capture import (
    detect_orange_region,
    detect_dark_cards,
    extract_avatars,
    load_library,
    match_avatar,
)

# 模块级缓存：头像库只加载一次
_library = None
_library_names = {}  # filename stem → display name 映射


def _get_library():
    global _library, _library_names
    if _library is None:
        _library = load_library()
        # 构建文件名 → 显示名映射（from pets_head directory）
        _library_names = {name: name for name in _library}
    return _library


def recognize_pets(image_path: str, top_n: int = 1) -> list[dict]:
    """
    识别截图中的所有敌方精灵。

    Returns:
        [{name, confidence, second_name, second_conf}, ...]
    """
    data = np.fromfile(image_path, dtype=np.uint8)
    bgr = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if bgr is None:
        return [{"error": f"无法读取图片: {image_path}"}]

    orange = detect_orange_region(bgr)
    if orange is None:
        return [{"error": "未检测到橙色面板"}]

    ox, oy, ow, oh = orange
    if ow < 300 or oh < 300:
        return [{"error": "橙色区域太小"}]

    panel = bgr[oy:oy + oh, ox:ox + ow]
    gray_panel = cv2.cvtColor(panel, cv2.COLOR_BGR2GRAY)
    cards = detect_dark_cards(gray_panel)

    if len(cards) < 4:
        return [{"error": f"仅检测到{len(cards)}张卡片，需要≥4张"}]

    library = _get_library()
    avatars = extract_avatars(panel, cards)
    results = []

    for i, av in enumerate(avatars):
        if av is None or av.size == 0:
            results.append({"slot": i + 1, "name": None, "confidence": 0})
            continue
        (name, score), second = match_avatar(av, library)
        results.append({
            "slot": i + 1,
            "name": name,
            "confidence": round(score, 4),
            "second_name": second[0] if second else None,
            "second_conf": round(second[1], 4) if second else None,
        })

    return results
