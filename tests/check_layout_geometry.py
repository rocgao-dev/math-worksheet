# -*- coding: utf-8 -*-
"""版式几何自检：打印页眉各栏位坐标区间、分隔线位置与题目区顶部。

用假 canvas 收集绘制指令，无需真正输出 PDF，便于快速核对
「栏位是否重叠」「第一行题目距离分隔线多远」。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from reportlab.pdfbase import pdfmetrics  # noqa: E402

from src.config import (  # noqa: E402
    MARGIN_RIGHT,
    MARGIN_TOP,
    PAGE_HEIGHT,
    PAGE_WIDTH,
    SheetConfig,
)
from src.layout import draw_header, register_fonts  # noqa: E402


class RecordingCanvas:
    def __init__(self) -> None:
        self.records: list[tuple] = []

    def setFont(self, font: str, size: float) -> None:
        self._font, self._size = font, size

    def drawCentredString(self, x, y, text) -> None:  # noqa: N802
        self.records.append(("centred", x, y, text, self._font, self._size))

    def drawRightString(self, x, y, text) -> None:  # noqa: N802
        self.records.append(("right", x, y, text, self._font, self._size))

    def drawString(self, x, y, text) -> None:  # noqa: N802
        self.records.append(("left", x, y, text, self._font, self._size))

    def setLineWidth(self, width) -> None:  # noqa: N802
        pass

    def line(self, x1, y1, x2, y2) -> None:  # noqa: N802
        self.records.append(("line", y1))


def main() -> int:
    register_fonts()
    cfg = SheetConfig(digit_pairs=((4, 4),), problems_per_page=6, pages=1,
                      date_str="2026-10-08")
    canvas = RecordingCanvas()
    area_top = draw_header(canvas, cfg, PAGE_HEIGHT - MARGIN_TOP)

    divider_y = None
    rows: set[float] = set()
    for rec in canvas.records:
        if rec[0] == "line":
            divider_y = rec[1]
        elif rec[0] in ("centred", "right", "left"):
            kind, x, y, text, font, size = rec
            width = pdfmetrics.stringWidth(text, font, size)
            left = x if kind == "left" else (x - width if kind == "right" else x - width / 2)
            right = left + width
            rows.add(round(y, 1))
            print(f"y={y:6.1f}  x=[{left:6.1f},{right:6.1f}]  {text}")

    print(f"\n纸张宽={PAGE_WIDTH:.1f}  右边距线 x={PAGE_WIDTH - MARGIN_RIGHT:.1f}")
    print(f"页眉行数（不同基线数）={len(rows)}  y 值={sorted(rows, reverse=True)}")
    print(f"分隔线 y={divider_y:.1f}  题目区顶部 y={area_top:.1f}"
          f"  第一行基线 y={area_top - cfg.font_size - 2:.1f}")
    print(f"题目区顶在分隔线下方 {divider_y - area_top:.1f}pt；"
          f"第一行基线距分隔线 {divider_y - (area_top - cfg.font_size - 2):.1f}pt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
