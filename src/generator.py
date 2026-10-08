"""题目生成器：按位数组合生成乘法算式，支持同页去重与随机种子复现。"""
from __future__ import annotations

import random
from typing import Iterable, Sequence

from .config import SheetConfig


def digit_bounds(digits: int) -> tuple[int, int]:
    """返回 d 位数的取数区间（闭区间），例如 3 -> (100, 999)。"""
    if digits < 1:
        raise ValueError("位数必须 >= 1")
    return 10 ** (digits - 1), 10**digits - 1


# ---------------------------------------------------------------- 严格数字规则
# 规则（默认开启，逐位校验）：
#   1) 不含 0 和 1；
#   2) 各位数字互不相同；
#   3) 相邻两位不能连续（相差 1，如 23 / 34 / 87）。
STRICT_DIGIT_POOL = "23456789"   # 可用数字池（已排除 0 与 1）
STRICT_MAX_TRIES = 300           # 拒绝采样次数上限


def _has_adjacent_consecutive(seq: Sequence[int]) -> bool:
    """相邻两位是否存在连续数字（相差 1）。"""
    return any(abs(seq[i] - seq[i + 1]) == 1 for i in range(len(seq) - 1))


def strict_number(digits: int, rng: random.Random) -> int:
    """生成符合严格规则的 digits 位数。

    数字从池 {2..9} 中不放回抽取（保证互不相同、不含 0/1），
    再拒绝相邻连续的组合。首位天然非 0（池中无 0）。
    """
    pool = [int(c) for c in STRICT_DIGIT_POOL]
    if digits > len(pool):
        raise ValueError(
            f"严格规则要求各位数字互不相同且不含 0/1，最多支持 {len(pool)} 位数，"
            f"收到 {digits} 位。请减少位数或关闭严格规则。"
        )
    for _ in range(STRICT_MAX_TRIES):
        picked = rng.sample(pool, digits)
        if not _has_adjacent_consecutive(picked):
            return int("".join(str(d) for d in picked))
    raise RuntimeError(
        f"严格规则下连续 {STRICT_MAX_TRIES} 次采样失败（{digits} 位数），请减少题量或关闭严格规则"
    )


def _rand_number(digits: int, rng: random.Random, strict: bool = True) -> int:
    if strict:
        return strict_number(digits, rng)
    lo, hi = digit_bounds(digits)
    return rng.randint(lo, hi)


def make_problem(
    a_digits: int,
    b_digits: int,
    rng: random.Random,
    strict: bool = True,
) -> tuple[int, int]:
    """生成一道 a_digits 位数 × b_digits 位数的乘法题。

    strict=True 时两个乘数都满足严格数字规则（不含 0/1、无重复数字、不相邻连续）。
    """
    return (
        _rand_number(a_digits, rng, strict),
        _rand_number(b_digits, rng, strict),
    )


def _key(a: int, b: int) -> tuple[int, int]:
    """无序去重键：a×b 与 b×a 视为同一题。"""
    return (a, b) if a <= b else (b, a)


def _rotate(pairs: Sequence[tuple[int, int]], index: int) -> tuple[int, int]:
    """按序轮转，使多种位数组合在整卷中尽量均衡分布。"""
    return pairs[index % len(pairs)]


def build_page_problems(
    cfg: SheetConfig,
    rng: random.Random,
    page_index: int,
    global_seen: set[tuple[int, int]],
) -> list[tuple[int, int]]:
    """生成一页题目。

    去重范围由 cfg.dedup_scope 决定（前提是 cfg.dedup 为 True）：
      - "page"（默认）：只保证本页/本天内不重复，跨页与跨天允许重复；
      - "sheet"：整卷、整批（含多天）全程不重复，通过 global_seen 跨页共享。
    """
    pairs = cfg.digit_pairs
    count = cfg.problems_per_page
    page_seen: set[tuple[int, int]] = set()
    problems: list[tuple[int, int]] = []

    max_attempts = count * 400 + 2000  # 防御性上限，避免极端参数下死循环
    attempts = 0
    idx = 0

    while len(problems) < count and attempts < max_attempts:
        attempts += 1
        a_digits, b_digits = _rotate(pairs, idx + page_index)
        idx += 1
        a, b = make_problem(a_digits, b_digits, rng, cfg.strict_digits)

        if cfg.dedup:
            key = _key(a, b)
            if key in page_seen:
                continue
            # page 范围：只保证本页/本天内不重复，跨页与跨天允许重复
            if cfg.dedup_scope == "sheet" and key in global_seen:
                continue
            page_seen.add(key)
            global_seen.add(key)

        problems.append((a, b))

    if len(problems) < count:
        raise RuntimeError(
            f"可用题目组合不足，无法生成 {count} 道不重复题目，请减少每页题数或调整位数组合"
        )
    return problems


def generate(cfg: SheetConfig, seed: int | None = None) -> list[list[tuple[int, int]]]:
    """生成整卷题目，返回按页分组的题目列表。

    参数
    ----
    cfg : SheetConfig
        已 normalize 的配置。
    seed : int | None
        若显式传入则覆盖 cfg.seed。
    """
    cfg.normalize()
    real_seed = cfg.seed if seed is None else seed
    rng = random.Random(real_seed)

    global_seen: set[tuple[int, int]] = set()
    pages: list[list[tuple[int, int]]] = []
    for page_index in range(cfg.pages):
        pages.append(build_page_problems(cfg, rng, page_index, global_seen))
    return pages


def generate_days(cfg: SheetConfig) -> list[list[list[tuple[int, int]]]]:
    """按配置的日期区间生成整批题目。

    返回 ``[每天][每页][题目]`` 三层结构：外层是日期，中层是该天的页，内层是题目。
    跨天仍共享同一个去重集合，确保整批不出现重复题目。
    """
    cfg.normalize()
    rng = random.Random(cfg.seed)

    global_seen: set[tuple[int, int]] = set()
    days: list[list[list[tuple[int, int]]]] = []
    page_no = 0
    for _d in cfg.date_list():
        day_pages: list[list[tuple[int, int]]] = []
        for _ in range(cfg.pages):
            day_pages.append(build_page_problems(cfg, rng, page_no, global_seen))
            page_no += 1
        days.append(day_pages)
    return days


def format_problem(a: int, b: int) -> str:
    """题面文本，例如 '1234 × 5678 ='。"""
    return f"{a} × {b} ="


def iterate_problems(pages: Iterable[Iterable[tuple[int, int]]]) -> Iterable[tuple[int, int]]:
    for page in pages:
        for problem in page:
            yield problem
