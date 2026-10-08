#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""命令行入口：生成 A4 乘法计算练习题 PDF。

示例
----
python generate.py --digits 4 --per-page 6 --date 2026-10-08
python generate.py --digits 4 --date 2026-10-09 --end-date 2026-10-31
python generate.py --digits 4 --date 2026-10-01 --end-date 2026-10-31 --weekdays mon,wed,fri
python generate.py --digits 3,4,5 --date 2026-10-01 --end-date 2026-10-31 --zip
python generate.py --date 2026-10-01 --end-date 2026-10-31 --dedup-scope sheet
"""
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.config import SheetConfig, default_output_path, parse_weekdays  # noqa: E402
from src.pdf_builder import build  # noqa: E402

DEDUP_SCOPE_CN = {"page": "仅同一天内不重复", "sheet": "整份不重复", "none": "不去重"}


def parse_digits(text: str) -> tuple[tuple[int, int], ...]:
    """把 "3,4,5" 解析为 ((3,3),(4,4),(5,5))；也支持 "3x4" 形式。"""
    pairs: list[tuple[int, int]] = []
    for token in text.replace("，", ",").split(","):
        token = token.strip().lower()
        if not token:
            continue
        if "x" in token or "*" in token or "×" in token:
            sep = "x" if "x" in token else ("*" if "*" in token else "×")
            a, b = token.split(sep)
            pairs.append((int(a), int(b)))
        else:
            d = int(token)
            pairs.append((d, d))
    return tuple(pairs)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="生成 A4 乘法计算练习题 PDF（支持日期区间批量出卷）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--digits", "-d", default="4",
                   help="乘数位数组合，逗号分隔；如 4 表示四位数×四位数，3,4,5 表示三种混合（默认 4）")
    p.add_argument("--per-page", "-n", type=int, default=6, help="每页题目数量（默认 6）")
    p.add_argument("--pages", "-p", type=int, default=1, help="每天页数（默认 1）")
    p.add_argument("--columns", "-c", type=int, default=2, help="每页列数（默认 2）")
    p.add_argument("--title", default="乘法计算练习", help="卷面标题")

    p.add_argument("--date", dest="date_str", default=date.today().isoformat(),
                   help="起始日期（单日即该天），默认今天（yyyy-MM-dd）")
    p.add_argument("--end-date", default="",
                   help="结束日期（yyyy-MM-dd）；填写后按区间批量出卷")
    p.add_argument("--weekdays", default="",
                   help="只在指定星期出卷，如 mon,wed,fri 或 1,3,5（1=周一）；留空=区间内每天都要")
    p.add_argument("--no-weekday", dest="show_weekday", action="store_false",
                   help="页眉日期不显示星期（默认显示，如 2026-10-09（周五））")
    p.set_defaults(show_weekday=True)

    p.add_argument("--font-size", type=int, default=14, help="题面字号（默认 14pt）")
    p.add_argument("--no-name", action="store_true", help="不显示“姓名”栏")
    p.add_argument("--no-class", action="store_true", help="不显示“班级”栏")
    p.add_argument("--time", dest="show_time", action="store_true", help="显示“用时”栏（默认已开启）")
    p.add_argument("--no-time", dest="show_time", action="store_false", help="隐藏“用时”栏")
    p.add_argument("--score", dest="show_score", action="store_true", help="显示“得分”栏（默认已开启）")
    p.add_argument("--no-score", dest="show_score", action="store_false", help="隐藏“得分”栏")
    p.set_defaults(show_time=True, show_score=True)

    p.add_argument("--no-dedup", action="store_true", help="关闭题目去重")
    p.add_argument("--dedup-scope", dest="dedup_scope", default="page",
                   choices=("page", "sheet"),
                   help="去重范围：page=同一天内不重复（默认，跨天可重复）；sheet=整份不重复")
    p.add_argument("--no-strict", action="store_true",
                   help="关闭严格数字规则（默认开启：不含 0/1、各位不重复、相邻不连号）")
    p.add_argument("--zip", dest="output_mode", action="store_const", const="zip", default="merge",
                   help="区间模式：每天一个 PDF 打包为 ZIP（默认合并为一个 PDF）")
    p.add_argument("--seed", type=int, default=None, help="随机种子，固定后可复现同一批题目")
    p.add_argument("-o", "--output", default="", help="输出文件路径，默认写入 examples/ 目录")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    dedup = not args.no_dedup
    cfg = SheetConfig(
        digit_pairs=parse_digits(args.digits),
        problems_per_page=args.per_page,
        pages=args.pages,
        columns=args.columns,
        title=args.title,
        date_str=args.date_str,
        date_end=args.end_date,
        weekdays=parse_weekdays(args.weekdays),
        show_weekday=args.show_weekday,
        output_mode=args.output_mode,
        show_name=not args.no_name,
        show_class=not args.no_class,
        show_time=args.show_time,
        show_score=args.show_score,
        dedup=dedup,
        dedup_scope=args.dedup_scope if dedup else "page",
        strict_digits=not args.no_strict,
        seed=args.seed,
        font_size=args.font_size,
    )
    cfg.normalize()

    out = args.output or default_output_path(cfg)
    path = build(cfg, out)

    days = cfg.date_list()
    total = len(days) * cfg.pages * cfg.problems_per_page
    kind = "ZIP（每天一个 PDF）" if cfg.output_mode == "zip" else "PDF"
    dedup_cn = DEDUP_SCOPE_CN["none"] if not cfg.dedup else DEDUP_SCOPE_CN[cfg.dedup_scope]
    print(f"[OK] 已生成 {kind}")
    print(f"     题型：{cfg.digits_label()} × {cfg.problems_per_page} 题/页 × {cfg.pages} 页/天")
    print(f"     日期：{cfg.start_date} → {cfg.end_date}（{len(days)} 天，共 {total} 题）"
          f"    星期显示：{'开' if cfg.show_weekday else '关'}")
    print(f"     列数：{cfg.columns}    去重：{dedup_cn}"
          f"    严格数字规则：{'开' if cfg.strict_digits else '关'}")
    print(f"     文件：{path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
