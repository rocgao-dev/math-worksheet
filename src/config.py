"""参数配置、A4 版式常量与字体解析。

本模块不依赖任何第三方库，供 generator / layout / pdf_builder / UI 共用。
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field, asdict
from datetime import date, timedelta
from pathlib import Path

# ---------------------------------------------------------------- 尺寸单位
MM = 2.834645669  # 1 mm = 2.834645669 pt

# A4 纵向（单位 pt）
PAGE_WIDTH = 210 * MM
PAGE_HEIGHT = 297 * MM

# 页边距
MARGIN_LEFT = 16 * MM
MARGIN_RIGHT = 16 * MM
MARGIN_TOP = 10 * MM
MARGIN_BOTTOM = 14 * MM

# 允许的乘数位数
DIGIT_CHOICES = (3, 4, 5)

# 中文/西文字体候选（按优先级）
FONT_REGULAR_CANDIDATES = (
    r"C:\Windows\Fonts\simhei.ttf",     # 黑体
    r"C:\Windows\Fonts\msyh.ttc",       # 微软雅黑
    r"C:\Windows\Fonts\simsun.ttc",     # 宋体
    r"C:\Windows\Fonts\Deng.ttf",       # 等线
)
FONT_BOLD_CANDIDATES = (
    r"C:\Windows\Fonts\simhei.ttf",
    r"C:\Windows\Fonts\msyhbd.ttc",
    r"C:\Windows\Fonts\Dengb.ttf",
)

FONT_NAME_REGULAR = "CJK-Regular"
FONT_NAME_BOLD = "CJK-Bold"

# 星期：0=周一 … 6=周日（与 datetime.date.weekday() 一致）
WEEKDAY_CN = ("一", "二", "三", "四", "五", "六", "日")
WEEKDAY_ALIASES = {
    "mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6,
    "周一": 0, "周二": 1, "周三": 2, "周四": 3, "周五": 4, "周六": 5, "周日": 6,
}


def find_font(candidates) -> str:
    """返回第一个存在且可读的字体文件路径。"""
    for path in candidates:
        if path and os.path.isfile(path):
            return path
    raise FileNotFoundError(
        "未找到可用中文字体，请检查系统字体目录：" + ", ".join(candidates)
    )


# ---------------------------------------------------------------- 日期工具
def parse_iso_date(text: str, field_name: str = "日期") -> date:
    """把 'yyyy-MM-dd' 解析为 date，并给出友好报错。"""
    text = (text or "").strip()
    if not text:
        raise ValueError(f"{field_name}不能为空")
    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"{field_name}格式应为 yyyy-MM-dd，收到 {text!r}") from exc


def format_date_label(d: date, show_weekday: bool = True) -> str:
    """日期展示文本，如 2026-10-09 或 2026-10-09（周五）。"""
    label = d.isoformat()
    if show_weekday:
        label += f"（周{WEEKDAY_CN[d.weekday()]}）"
    return label


def parse_weekdays(text: str) -> tuple[int, ...]:
    """解析星期筛选，如 'mon,wed,fri' / '周一,周三' / '1,3,5'（1=周一…7=周日）。

    返回按周一…周日排序、去重的元组；空串返回空元组（表示不限定）。
    """
    if not text or not str(text).strip():
        return ()
    found: set[int] = set()
    for token in str(text).replace("，", ",").split(","):
        token = token.strip().lower()
        if not token:
            continue
        if token in WEEKDAY_ALIASES:
            found.add(WEEKDAY_ALIASES[token])
        elif token.isdigit() and 1 <= int(token) <= 7:
            found.add(int(token) - 1)   # 用户习惯 1=周一
        else:
            raise ValueError(f"无法识别的星期：{token!r}（可用 mon/wed 或 1-7 或 周一）")
    return tuple(sorted(found))


@dataclass
class SheetConfig:
    """一张（或一批）练习卷的全部生成参数。"""

    # 乘数位数组合，每一项形如 (3, 3) 表示“三位数 × 三位数”
    digit_pairs: tuple[tuple[int, int], ...] = ((4, 4),)

    problems_per_page: int = 6       # 每页题目数量
    pages: int = 1                   # 每天页数
    columns: int = 2                 # 每页列数（行数由题量与列数推算）

    title: str = "乘法计算练习"
    # 起始日期（单日模式即为当天；区间模式为起始日）
    date_str: str = field(default_factory=lambda: date.today().isoformat())
    date_end: str = ""               # 结束日期；为空表示只生成 date_str 一天
    weekdays: tuple[int, ...] = ()   # 仅生成这些星期（0=周一…6=周日），空=每天
    show_weekday: bool = True        # 页眉日期是否附带“（周X）”
    output_mode: str = "merge"       # merge=合并为一个 PDF；zip=每天一个 PDF 打包

    show_name: bool = True           # 页眉是否显示“姓名____”
    show_class: bool = True          # 页眉是否显示“班级____”
    show_time: bool = True           # 页眉是否显示“用时____”
    show_score: bool = True          # 页眉是否显示“得分____”

    dedup: bool = True               # 题目去重开关
    # 去重范围：page=只保证“同一页/同一天”内不重复（跨页、跨天可重复，默认）；
    #           sheet=整卷（含多天）全程不重复
    dedup_scope: str = "page"
    # 严格数字规则：每个乘数不含 0/1、各位数字互不相同、相邻两位不连续
    strict_digits: bool = True
    seed: int | None = None          # 随机种子，None 表示每次不同
    out_path: str = ""               # 输出 PDF 路径

    # 题面字号（pt），行高与作答空间随之伸缩
    font_size: int = 14
    header_font_size: int = 12
    title_font_size: int = 18

    # ---------------------------------------------------------- 校验
    def normalize(self) -> "SheetConfig":
        """把用户输入规整为合法值，返回自身便于链式调用。"""
        pairs: list[tuple[int, int]] = []
        for item in self.digit_pairs:
            if isinstance(item, int):
                item = (item, item)
            a, b = int(item[0]), int(item[1])
            if a < 1 or b < 1:
                raise ValueError(f"乘数位数必须为正整数，收到 {item!r}")
            if (a, b) not in pairs:
                pairs.append((a, b))
        if not pairs:
            raise ValueError("至少需要选择一种乘数位数组合")
        self.digit_pairs = tuple(pairs)

        self.problems_per_page = max(1, int(self.problems_per_page))
        self.pages = max(1, int(self.pages))
        self.columns = max(1, int(self.columns))
        self.font_size = max(8, int(self.font_size))

        self.date_str = parse_iso_date(self.date_str, "起始日期").isoformat()
        if self.date_end:
            end = parse_iso_date(self.date_end, "结束日期")
            if end < date.fromisoformat(self.date_str):
                raise ValueError("结束日期不能早于起始日期")
            self.date_end = end.isoformat()
        self.weekdays = tuple(sorted({int(w) for w in self.weekdays}))
        for w in self.weekdays:
            if not 0 <= w <= 6:
                raise ValueError(f"星期取值应在 0-6（0=周一），收到 {w}")
        if self.output_mode not in ("merge", "zip"):
            raise ValueError(f"输出形式应为 merge 或 zip，收到 {self.output_mode!r}")
        if self.dedup_scope not in ("page", "sheet"):
            raise ValueError(f"去重范围应为 page 或 sheet，收到 {self.dedup_scope!r}")
        return self

    def to_dict(self) -> dict:
        d = asdict(self)
        d["digit_pairs"] = [list(p) for p in self.digit_pairs]
        return d

    # ---------------------------------------------------------- 日期
    @property
    def start_date(self) -> date:
        return date.fromisoformat(self.date_str)

    @property
    def end_date(self) -> date:
        return date.fromisoformat(self.date_end) if self.date_end else self.start_date

    @property
    def is_range(self) -> bool:
        return bool(self.date_end) and self.end_date > self.start_date

    def date_list(self) -> list[date]:
        """展开需要出卷的日期（含端点），并按 weekdays 过滤。"""
        start, end = self.start_date, self.end_date
        days = [start + timedelta(days=i) for i in range((end - start).days + 1)]
        if self.weekdays:
            days = [d for d in days if d.weekday() in self.weekdays]
        if not days:
            raise ValueError("按当前星期筛选后，区间内没有符合条件的日期，请调整区间或星期")
        return days

    def date_label(self, d: date | None = None) -> str:
        return format_date_label(d or self.start_date, self.show_weekday)

    # ---------------------------------------------------------- 展示
    def digits_label(self) -> str:
        return "、".join(f"{a}位数×{b}位数" for a, b in self.digit_pairs)

    @property
    def rows_per_page(self) -> int:
        return -(-self.problems_per_page // self.columns)  # 向上取整


def date_range_tag(cfg: SheetConfig) -> str:
    """文件名中的日期部分：单日为 2026-10-09，区间为 2026-10-09_至_2026-10-31。"""
    if cfg.is_range:
        return f"{cfg.start_date.isoformat()}_至_{cfg.end_date.isoformat()}"
    return cfg.start_date.isoformat()


def default_output_path(cfg: SheetConfig, base_dir: str | os.PathLike | None = None) -> str:
    """生成默认输出文件名，例如 乘法计算练习_4x4_2026-10-09.pdf。"""
    base = Path(base_dir) if base_dir else Path(__file__).resolve().parent.parent / "examples"
    tag = "_".join(f"{a}x{b}" for a, b in cfg.digit_pairs)
    suffix = ".zip" if cfg.output_mode == "zip" else ".pdf"
    name = f"{cfg.title}_{tag}_{date_range_tag(cfg)}{suffix}"
    return str(base / name)
