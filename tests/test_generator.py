# -*- coding: utf-8 -*-
"""出题器单元测试：位数区间、题量、去重范围、随机种子复现、严格数字规则、日期区间、配置校验。"""
from __future__ import annotations

import random
import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import (  # noqa: E402
    SheetConfig,
    date_range_tag,
    default_output_path,
    format_date_label,
    parse_weekdays,
)
from src.generator import (  # noqa: E402
    _key,
    build_page_problems,
    digit_bounds,
    generate,
    generate_days,
    make_problem,
    strict_number,
)


class TestDigitBounds(unittest.TestCase):
    def test_bounds(self):
        self.assertEqual(digit_bounds(1), (1, 9))
        self.assertEqual(digit_bounds(3), (100, 999))
        self.assertEqual(digit_bounds(4), (1000, 9999))
        self.assertEqual(digit_bounds(5), (10000, 99999))

    def test_invalid(self):
        with self.assertRaises(ValueError):
            digit_bounds(0)


class TestMakeProblem(unittest.TestCase):
    def test_number_range(self):
        rng = random.Random(42)
        for digits in (3, 4, 5):
            lo, hi = digit_bounds(digits)
            for _ in range(200):
                a, b = make_problem(digits, digits, rng)
                self.assertTrue(lo <= a <= hi, f"{a} 超出 {digits} 位数区间")
                self.assertTrue(lo <= b <= hi, f"{b} 超出 {digits} 位数区间")

    def test_mixed_pairs(self):
        rng = random.Random(1)
        a, b = make_problem(3, 5, rng)
        self.assertTrue(100 <= a <= 999)
        self.assertTrue(10000 <= b <= 99999)


class TestStrictDigits(unittest.TestCase):
    """严格数字规则：不含 0/1、各位数字互不相同、相邻两位不连续。"""

    def _check(self, n: int, digits: int):
        s = str(n)
        self.assertEqual(len(s), digits, f"{n} 不是 {digits} 位数")
        self.assertNotIn("0", s, f"{n} 含 0")
        self.assertNotIn("1", s, f"{n} 含 1")
        self.assertEqual(len(set(s)), len(s), f"{n} 存在重复数字")
        for i in range(len(s) - 1):
            diff = abs(int(s[i]) - int(s[i + 1]))
            self.assertNotEqual(diff, 1, f"{n} 存在相邻连续数字 {s[i]}{s[i + 1]}")

    def test_strict_number_4(self):
        rng = random.Random(2026)
        for _ in range(500):
            self._check(strict_number(4, rng), 4)

    def test_strict_number_3_and_5(self):
        rng = random.Random(7)
        for _ in range(300):
            self._check(strict_number(3, rng), 3)
            self._check(strict_number(5, rng), 5)

    def test_make_problem_strict_default_on(self):
        rng = random.Random(99)
        for _ in range(200):
            a, b = make_problem(4, 4, rng)
            self._check(a, 4)
            self._check(b, 4)

    def test_generate_strict_page(self):
        cfg = SheetConfig(digit_pairs=((4, 4),), problems_per_page=12, pages=1, seed=2026)
        pages = generate(cfg)
        self.assertEqual(len(pages[0]), 12)
        for a, b in pages[0]:
            self._check(a, 4)
            self._check(b, 4)

    def test_strict_disabled_allows_any_digits(self):
        rng = random.Random(1)
        chars = set()
        for _ in range(200):
            a, b = make_problem(4, 4, rng, strict=False)
            chars.update(str(a) + str(b))
        self.assertTrue(any(c in chars for c in "01"),
                        "关闭严格规则后应能出现 0/1")

    def test_strict_too_many_digits_raises(self):
        rng = random.Random(0)
        with self.assertRaises(ValueError):
            strict_number(9, rng)


class TestGenerate(unittest.TestCase):
    def test_problem_count(self):
        cfg = SheetConfig(digit_pairs=((4, 4),), problems_per_page=12, pages=3)
        pages = generate(cfg)
        self.assertEqual(len(pages), 3)
        for page in pages:
            self.assertEqual(len(page), 12)

    def test_dedup_within_page(self):
        cfg = SheetConfig(digit_pairs=((3, 3),), problems_per_page=30, pages=1, seed=7)
        pages = generate(cfg)
        keys = [_key(a, b) for a, b in pages[0]]
        self.assertEqual(len(keys), len(set(keys)), "同一页出现重复题目")

    def test_dedup_across_pages_sheet_scope(self):
        cfg = SheetConfig(digit_pairs=((3, 3),), problems_per_page=20, pages=3,
                          dedup_scope="sheet", seed=9)
        pages = generate(cfg)
        all_keys = [_key(a, b) for page in pages for a, b in page]
        self.assertEqual(len(all_keys), len(set(all_keys)), "整份范围下跨页出现重复题目")

    def test_no_dedup_allows_duplicates_maybe(self):
        cfg = SheetConfig(digit_pairs=((3, 3),), problems_per_page=5, pages=1,
                          dedup=False, seed=3)
        pages = generate(cfg)
        self.assertEqual(len(pages[0]), 5)

    def test_seed_reproducible(self):
        cfg1 = SheetConfig(digit_pairs=((4, 4),), problems_per_page=10, pages=2, seed=123)
        cfg2 = SheetConfig(digit_pairs=((4, 4),), problems_per_page=10, pages=2, seed=123)
        self.assertEqual(generate(cfg1), generate(cfg2))

    def test_seed_override(self):
        cfg = SheetConfig(digit_pairs=((4, 4),), problems_per_page=6, pages=1)
        self.assertEqual(generate(cfg, seed=5), generate(cfg, seed=5))

    def test_mixed_digits_balanced(self):
        cfg = SheetConfig(digit_pairs=((3, 3), (4, 4), (5, 5)), problems_per_page=12, pages=1, seed=11)
        pages = generate(cfg)
        from collections import Counter
        counter = Counter()
        for a, b in pages[0]:
            counter[(len(str(a)), len(str(b)))] += 1
        # 三种组合轮转，每种应出现 4 次
        self.assertEqual(counter[(3, 3)], 4)
        self.assertEqual(counter[(4, 4)], 4)
        self.assertEqual(counter[(5, 5)], 4)


class TestDedupScope(unittest.TestCase):
    """去重范围：page=只保证同一天/同一页内不重复（默认，跨天可重复）；sheet=整份不重复。"""

    def test_default_scope_is_page(self):
        self.assertTrue(SheetConfig().dedup)
        self.assertEqual(SheetConfig().dedup_scope, "page")

    def test_bad_scope_raises(self):
        with self.assertRaises(ValueError):
            SheetConfig(dedup_scope="bad").normalize()

    def test_page_scope_ignores_global_seen(self):
        """page 范围下，别处（其他页/其他天）用过的题不会阻止本页生成，即允许重复。"""
        cfg = SheetConfig(digit_pairs=((3, 3),), problems_per_page=6,
                          dedup_scope="page", seed=2026)
        first = build_page_problems(cfg, random.Random(1), 0, set())
        keys_first = {_key(a, b) for a, b in first}
        again = build_page_problems(cfg, random.Random(1), 0, set(keys_first))
        self.assertEqual(first, again, "page 范围不应受其他页/天的去重集合影响")

    def test_sheet_scope_respects_global_seen(self):
        """sheet 范围下，其他页/天用过的题会被避开。"""
        cfg = SheetConfig(digit_pairs=((3, 3),), problems_per_page=6,
                          dedup_scope="sheet", seed=2026)
        first = build_page_problems(cfg, random.Random(1), 0, set())
        keys_first = {_key(a, b) for a, b in first}
        again = build_page_problems(cfg, random.Random(1), 0, set(keys_first))
        self.assertNotEqual(first, again)
        self.assertFalse(keys_first & {_key(a, b) for a, b in again})

    def test_page_scope_dedup_within_page(self):
        cfg = SheetConfig(digit_pairs=((4, 4),), problems_per_page=6, pages=1,
                          dedup_scope="page", seed=11)
        pages = generate(cfg)
        keys = [_key(a, b) for a, b in pages[0]]
        self.assertEqual(len(keys), len(set(keys)), "同一天内出现重复题目")

    def test_page_scope_multi_day_still_complete(self):
        """page 范围下多天批量不会因去重池枯竭而报“组合不足”。"""
        cfg = SheetConfig(digit_pairs=((4, 4),), problems_per_page=6, pages=1,
                          date_str="2026-10-09", date_end="2026-10-31", seed=5)
        days = generate_days(cfg)
        self.assertEqual(len(days), 23)


class TestDateRange(unittest.TestCase):
    """日期区间、星期筛选、页眉日期（星期）与批量生成结构。"""

    def test_single_day(self):
        cfg = SheetConfig(date_str="2026-10-09").normalize()
        self.assertFalse(cfg.is_range)
        self.assertEqual([d.isoformat() for d in cfg.date_list()], ["2026-10-09"])

    def test_range_inclusive(self):
        cfg = SheetConfig(date_str="2026-10-09", date_end="2026-10-12").normalize()
        self.assertTrue(cfg.is_range)
        self.assertEqual(
            [d.isoformat() for d in cfg.date_list()],
            ["2026-10-09", "2026-10-10", "2026-10-11", "2026-10-12"],
        )

    def test_range_reversed_raises(self):
        with self.assertRaises(ValueError):
            SheetConfig(date_str="2026-10-12", date_end="2026-10-09").normalize()

    def test_weekday_filter(self):
        # 2026-10-09 是周五；只保留周一/周三/周五
        cfg = SheetConfig(date_str="2026-10-09", date_end="2026-10-18",
                          weekdays=(0, 2, 4)).normalize()
        days = cfg.date_list()
        self.assertTrue(all(d.weekday() in (0, 2, 4) for d in days))
        self.assertEqual(
            [d.isoformat() for d in days],
            ["2026-10-09", "2026-10-12", "2026-10-14", "2026-10-16"],
        )

    def test_weekday_filter_empty_raises(self):
        # 2026-10-10/11 是周六、周日，只留周一则无符合日期
        cfg = SheetConfig(date_str="2026-10-10", date_end="2026-10-11",
                          weekdays=(0,)).normalize()
        with self.assertRaises(ValueError):
            cfg.date_list()

    def test_parse_weekdays_aliases(self):
        self.assertEqual(parse_weekdays("mon,wed,fri"), (0, 2, 4))
        self.assertEqual(parse_weekdays("周一,周三"), (0, 2))
        self.assertEqual(parse_weekdays("1,3,5"), (0, 2, 4))
        self.assertEqual(parse_weekdays(""), ())
        self.assertEqual(parse_weekdays("fri,mon,fri"), (0, 4))
        with self.assertRaises(ValueError):
            parse_weekdays("星期八")

    def test_format_date_label(self):
        d = date(2026, 10, 9)
        self.assertEqual(format_date_label(d), "2026-10-09（周五）")
        self.assertEqual(format_date_label(d, show_weekday=False), "2026-10-09")

    def test_date_label_method(self):
        cfg = SheetConfig(date_str="2026-10-09", show_weekday=True).normalize()
        self.assertEqual(cfg.date_label(), "2026-10-09（周五）")
        cfg2 = SheetConfig(date_str="2026-10-09", show_weekday=False).normalize()
        self.assertEqual(cfg2.date_label(), "2026-10-09")

    def test_date_range_tag(self):
        one = SheetConfig(date_str="2026-10-09").normalize()
        self.assertEqual(date_range_tag(one), "2026-10-09")
        span = SheetConfig(date_str="2026-10-09", date_end="2026-10-31").normalize()
        self.assertEqual(date_range_tag(span), "2026-10-09_至_2026-10-31")

    def test_output_mode_and_suffix(self):
        pdf_cfg = SheetConfig(date_str="2026-10-09").normalize()
        self.assertTrue(default_output_path(pdf_cfg).endswith(".pdf"))
        zip_cfg = SheetConfig(date_str="2026-10-09", output_mode="zip").normalize()
        self.assertTrue(default_output_path(zip_cfg).endswith(".zip"))
        with self.assertRaises(ValueError):
            SheetConfig(output_mode="bad").normalize()

    def test_generate_days_sheet_scope_no_duplicates(self):
        cfg = SheetConfig(
            digit_pairs=((3, 3),), problems_per_page=5, pages=2,
            date_str="2026-10-09", date_end="2026-10-11",
            dedup_scope="sheet", seed=2026,
        ).normalize()
        days = generate_days(cfg)
        self.assertEqual(len(days), 3)        # 三天
        self.assertEqual(len(days[0]), 2)     # 每天两页
        keys = [_key(a, b) for day in days for page in day for a, b in page]
        self.assertEqual(len(keys), 30)
        self.assertEqual(len(keys), len(set(keys)), "整份范围下跨天出现重复题目")

    def test_generate_days_page_scope_dedup_per_day(self):
        """默认 page 范围：每天（每页）内部不重复即可，跨天允许重复。"""
        cfg = SheetConfig(
            digit_pairs=((3, 3),), problems_per_page=6, pages=1,
            date_str="2026-10-09", date_end="2026-10-11", seed=2026,
        ).normalize()
        days = generate_days(cfg)
        self.assertEqual(len(days), 3)
        for day in days:
            keys = [_key(a, b) for a, b in day[0]]
            self.assertEqual(len(keys), len(set(keys)), "同一天内出现重复题目")


class TestConfigValidation(unittest.TestCase):
    def test_empty_digits_raises(self):
        cfg = SheetConfig(digit_pairs=())
        with self.assertRaises(ValueError):
            cfg.normalize()

    def test_normalize_clamps(self):
        cfg = SheetConfig(digit_pairs=(4,), problems_per_page=0, pages=0, columns=0)
        cfg.normalize()
        self.assertEqual(cfg.digit_pairs, ((4, 4),))
        self.assertGreaterEqual(cfg.problems_per_page, 1)
        self.assertGreaterEqual(cfg.pages, 1)
        self.assertGreaterEqual(cfg.columns, 1)

    def test_rows_per_page(self):
        cfg = SheetConfig(digit_pairs=((4, 4),), problems_per_page=13, columns=3)
        self.assertEqual(cfg.rows_per_page, 5)

    def test_strict_default_on(self):
        self.assertTrue(SheetConfig().strict_digits)


if __name__ == "__main__":
    unittest.main(verbosity=2)
