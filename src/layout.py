"""A4 版式绘制：页眉（标题/日期/姓名/班级/用时/得分）、题目网格、页脚页码。

仅使用 reportlab 的 canvas 低层接口，便于精确控制 A4 排版。
"""
from __future__ import annotations

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from .config import (
    FONT_BOLD_CANDIDATES,
    FONT_NAME_BOLD,
    FONT_NAME_REGULAR,
    FONT_REGULAR_CANDIDATES,
    MARGIN_BOTTOM,
    MARGIN_LEFT,
    MARGIN_RIGHT,
    MARGIN_TOP,
    PAGE_HEIGHT,
    PAGE_WIDTH,
    SheetConfig,
    find_font,
)

_REGISTERED = False


def register_fonts() -> None:
    """注册中文字体，全局只执行一次。"""
    global _REGISTERED
    if _REGISTERED:
        return

    regular_path = find_font(FONT_REGULAR_CANDIDATES)
    try:
        bold_path = find_font(FONT_BOLD_CANDIDATES)
    except FileNotFoundError:
        bold_path = regular_path

    pdfmetrics.registerFont(TTFont(FONT_NAME_REGULAR, regular_path))

    try:
        if bold_path.lower().endswith(".ttc"):
            pdfmetrics.registerFont(TTFont(FONT_NAME_BOLD, bold_path, subfontIndex=0))
        else:
            pdfmetrics.registerFont(TTFont(FONT_NAME_BOLD, bold_path))
    except Exception:
        pdfmetrics.registerFont(TTFont(FONT_NAME_BOLD, regular_path))

    _REGISTERED = True


def _fit_font_size(text: str, font: str, max_width: float, size: float, min_size: float = 9.0) -> float:
    """按格宽自动收缩字号，保证长算式不越界。"""
    while size > min_size and pdfmetrics.stringWidth(text, font, size) > max_width:
        size -= 0.5
    return size


def draw_header(
    c: "canvas.Canvas",  # noqa: F821
    cfg: SheetConfig,
    top_y: float,
    date_label: str | None = None,
) -> float:
    """绘制页眉，返回题目区可用的顶部 y 坐标。

    左侧栏位（姓名/班级/用时/得分）依次排布，右上放日期；
    ``date_label`` 用于覆盖页眉日期文本（如按天生成时传入当天日期）；
    传空字符串则不绘制日期。
    """
    y = top_y
    label = cfg.date_str if date_label is None else date_label

    # 标题（居中）与日期（右上）同处一行，为下方栏位腾出整行宽度
    c.setFont(FONT_NAME_BOLD, cfg.title_font_size)
    y -= cfg.title_font_size
    c.drawCentredString(PAGE_WIDTH / 2, y, cfg.title)
    if label:
        c.setFont(FONT_NAME_REGULAR, cfg.header_font_size)
        c.drawRightString(PAGE_WIDTH - MARGIN_RIGHT, y, f"日期：{label}")
    y -= 8

    c.setFont(FONT_NAME_REGULAR, cfg.header_font_size)
    hf = cfg.header_font_size
    line_y = y - hf

    # 栏位独占整行宽度（右侧已无日期占位）
    right_limit = PAGE_WIDTH - MARGIN_RIGHT

    items: list[str] = []
    if cfg.show_name:
        items.append("姓名：____________")
    if cfg.show_class:
        items.append("班级：__________")
    if cfg.show_time:
        items.append("用时：________")
    if cfg.show_score:
        items.append("得分：__________")

    gap = 18.0
    x = MARGIN_LEFT
    for item in items:
        w = pdfmetrics.stringWidth(item, FONT_NAME_REGULAR, hf)
        if x > MARGIN_LEFT:
            if x + gap + w > right_limit:
                # 本行放不下：换行，从左侧重新开始
                line_y -= hf + 4
                x = MARGIN_LEFT
            else:
                x += gap
        c.drawString(x, line_y, item)
        x += w

    y = line_y - 6
    c.setLineWidth(0.8)
    c.line(MARGIN_LEFT, y, PAGE_WIDTH - MARGIN_RIGHT, y)

    # 题目区顶部：紧贴分隔线，避免第一行上方留出空白
    return y - 2


def draw_footer(c: "canvas.Canvas", page_no: int, total_pages: int) -> None:  # noqa: F821
    c.setFont(FONT_NAME_REGULAR, 10)
    c.drawCentredString(PAGE_WIDTH / 2, MARGIN_BOTTOM - 6, f"第 {page_no} / {total_pages} 页")


def draw_problems(
    c: "canvas.Canvas",
    cfg: SheetConfig,
    problems: list[tuple[int, int]],
    area_top: float,
    area_bottom: float,
) -> None:
    """按 columns × rows 网格绘制题目。

    每道题采用「格内顶部对齐」，使第一行紧贴页眉分隔线；行高仍按可用空间均分，
    为竖式计算保留足够书写空间。
    """
    columns = cfg.columns
    rows = max(1, -(-len(problems) // columns))

    content_width = PAGE_WIDTH - MARGIN_LEFT - MARGIN_RIGHT
    cell_w = content_width / columns
    cell_h = (area_top - area_bottom) / rows

    for index, (a, b) in enumerate(problems):
        row = index // columns
        col = index % columns

        cell_left = MARGIN_LEFT + col * cell_w
        cell_top = area_top - row * cell_h
        # 顶部对齐：题面距格顶约一个字高，不再垂直居中
        baseline = cell_top - cfg.font_size - 2

        text = f"{a} × {b} ="
        size = _fit_font_size(text, FONT_NAME_REGULAR, cell_w - 24, cfg.font_size)
        c.setFont(FONT_NAME_REGULAR, size)
        c.drawString(cell_left + 12, baseline, text)


def draw_page(
    c: "canvas.Canvas",
    cfg: SheetConfig,
    problems: list[tuple[int, int]],
    page_no: int,
    total_pages: int,
    date_label: str | None = None,
) -> None:  # noqa: F821
    """绘制单页（调用方负责 showPage / save）。

    ``date_label`` 用于页眉日期；批量生成时逐页传入当天日期。
    """
    register_fonts()

    top_y = PAGE_HEIGHT - MARGIN_TOP
    area_top = draw_header(c, cfg, top_y, date_label)
    area_bottom = MARGIN_BOTTOM + 12

    draw_problems(c, cfg, problems, area_top, area_bottom)
    draw_footer(c, page_no, total_pages)
