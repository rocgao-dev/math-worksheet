# -*- coding: utf-8 -*-
"""示例：默认「页面内去重」，验证每天 6 题不重复、跨天可重复。"""
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

from src.config import SheetConfig, default_output_path  # noqa: E402
from src.generator import _key, generate_days  # noqa: E402
from src.pdf_builder import build  # noqa: E402

cfg = SheetConfig(
    digit_pairs=((4, 4),),
    problems_per_page=6,
    pages=1,
    date_str="2026-10-09",
    date_end="2026-10-31",
    weekdays=(0, 2, 4),      # 周一/周三/周五
    dedup_scope="page",      # 默认：每天内不重复
    seed=2026,
).normalize()

days = cfg.date_list()
probs = generate_days(cfg)

all_keys = []
print(f"天数：{len(days)}")
for d, day in zip(days, probs):
    keys = [_key(a, b) for a, b in day[0]]
    inside_ok = len(keys) == len(set(keys))
    all_keys.extend(keys)
    cells = "  ".join(f"{a} × {b}" for a, b in day[0])
    print(f"  {d.isoformat()}（{len(keys)} 题，页内唯一={inside_ok}）: {cells}")

dup_pairs = len(all_keys) - len(set(all_keys))
print(f"总题数：{len(all_keys)}    跨天重复题目数：{dup_pairs}（page 范围下允许 > 0）")

out = default_output_path(cfg)
path = build(cfg, out)
print(f"文件：{path}")
