"""生成日期区间演示产物：每周一/三/五，2026-10-09 ~ 2026-10-31。

输出两份：
  1) 合并 PDF（所有天拼成一份多页 PDF，每天页眉日期不同）
  2) ZIP（每天一个独立 PDF）
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config import SheetConfig  # noqa: E402
from src.pdf_builder import build  # noqa: E402

EX = ROOT / "examples"

BASE = dict(
    digit_pairs=((4, 4),),
    problems_per_page=6,
    pages=1,
    date_str="2026-10-09",
    date_end="2026-10-31",
    weekdays=(0, 2, 4),   # 周一 / 周三 / 周五
    show_weekday=True,
    seed=20261,
)

merged = build(SheetConfig(**BASE, output_mode="merge"),
               str(EX / "乘法计算练习_4x4_区间1009至1031_周一三五_合并.pdf"))
print("MERGED", merged)

zipped = build(SheetConfig(**BASE, output_mode="zip"),
               str(EX / "乘法计算练习_4x4_区间1009至1031_周一三五.zip"))
print("ZIP", zipped)
