# -*- coding: utf-8 -*-
"""示例：页脚励志短语（写给 12 岁初一男生）。

生成两份：
  1) 日期区间合并 PDF：每天 1 页 6 题，页脚短语逐页随机（内置词库）
  2) 单日单页 PDF：页面居中显示自定义短语，便于快速预览版式
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config import SheetConfig  # noqa: E402
from src.pdf_builder import build  # noqa: E402

EX = ROOT / "examples"

# 1) 区间合并：2026-10-12 ~ 2026-10-21（10 天），每天 1 页 6 题，页脚短语随机
range_cfg = SheetConfig(
    digit_pairs=((4, 4),),
    problems_per_page=6,
    pages=1,
    date_str="2026-10-12",
    date_end="2026-10-21",
    show_quote=True,
    seed=20261012,
)
range_path = build(range_cfg, str(EX / "乘法计算练习_4x4_页脚短语_2026-10-12至10-21.pdf"))
print("RANGE", range_path)

# 2) 单日单页：自定义短语
single_cfg = SheetConfig(
    digit_pairs=((4, 4),),
    problems_per_page=6,
    pages=1,
    date_str="2026-10-12",
    quote_text="每天进步一点点，坚持就是胜利。",
    seed=20261012,
)
single_path = build(single_cfg, str(EX / "乘法计算练习_4x4_页脚短语_单日自定义.pdf"))
print("SINGLE", single_path)
