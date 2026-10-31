# -*- coding: utf-8 -*-
"""无依赖生成 32x32 程序图标（蓝色圆角方块 + 白色对勾）。

输出 32 位 BMP 内核的 ICO 文件，Windows Vista 及以上均支持。
"""
from __future__ import annotations

import math
import struct
from pathlib import Path

SIZE = 32
RADIUS = 7
BG = (0x4f, 0x8c, 0xff)   # #4f8cff (RGB)
FG = (0xff, 0xff, 0xff)


def _in_rounded_rect(x: int, y: int) -> bool:
    if x < RADIUS and y < RADIUS:
        return math.hypot(x - RADIUS, y - RADIUS) <= RADIUS
    if x >= SIZE - RADIUS and y < RADIUS:
        return math.hypot(x - (SIZE - 1 - RADIUS), y - RADIUS) <= RADIUS
    if x < RADIUS and y >= SIZE - RADIUS:
        return math.hypot(x - RADIUS, y - (SIZE - 1 - RADIUS)) <= RADIUS
    if x >= SIZE - RADIUS and y >= SIZE - RADIUS:
        return math.hypot(x - (SIZE - 1 - RADIUS),
                          y - (SIZE - 1 - RADIUS)) <= RADIUS
    return True


def _dist_to_segment(px, py, ax, ay, bx, by) -> float:
    dx, dy = bx - ax, by - ay
    if dx == dy == 0:
        return math.hypot(px - ax, py - ay)
    t = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    qx, qy = ax + t * dx, ay + t * dy
    return math.hypot(px - qx, py - qy)


def _is_check(x: int, y: int) -> bool:
    # 对勾两段：(8,18)->(14,24) 和 (14,24)->(24,9)
    return (
        _dist_to_segment(x, y, 8, 18, 14, 24) < 1.7
        or _dist_to_segment(x, y, 14, 24, 24, 9) < 1.7
    )


def build_pixels() -> list[tuple[int, int, int, int]]:
    # 自上而下的 BGRA 像素（写 BMP 时再翻转）
    rows = []
    for y in range(SIZE):
        row = []
        for x in range(SIZE):
            if not _in_rounded_rect(x, y):
                row.append((0, 0, 0, 0))
            elif _is_check(x, y):
                row.append((FG[2], FG[1], FG[0], 255))
            else:
                row.append((BG[2], BG[1], BG[0], 255))
        rows.append(row)
    return rows


def write_ico(path: Path) -> None:
    pixels = build_pixels()
    # BITMAPINFOHEADER
    info = struct.pack(
        "<IiiHHIIiiII",
        40, SIZE, SIZE * 2, 1, 32, 0,
        SIZE * SIZE * 4, 0, 0, 0, 0,
    )
    xor = bytearray()
    for y in range(SIZE - 1, -1, -1):       # 自下而上
        for b, g, r, a in pixels[y]:
            xor += struct.pack("<BBBB", b, g, r, a)
    # AND 掩码：每行按 4 字节对齐，32 像素 = 4 字节，全 0（由 alpha 控制透明）
    and_mask = b"\x00" * (SIZE * 4)
    image = info + bytes(xor) + and_mask

    # ICONDIR
    header = struct.pack("<HHH", 0, 1, 1)
    # ICONDIRENTRY
    entry = struct.pack(
        "<BBBBHHII",
        SIZE, SIZE, 0, 0, 1, 32, len(image), 6 + 16,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(header + entry + image)


if __name__ == "__main__":
    out = Path(__file__).resolve().parent / "app.ico"
    write_ico(out)
    print("icon written:", out, out.stat().st_size, "bytes")
