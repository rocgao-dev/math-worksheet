"""把题目组装为 A4 纵向 PDF。

支持三种产出：
- 单日 / 日期区间 → 合并为一个 PDF（每天从新页开始，页眉日期跟随当天）
- 日期区间 → 每天一个独立 PDF，打包为 ZIP
"""
from __future__ import annotations

import io
import os
import zipfile
from pathlib import Path

from reportlab.pdfgen import canvas

from .config import (
    PAGE_HEIGHT,
    PAGE_WIDTH,
    SheetConfig,
    date_range_tag,
    default_output_path,
)
from .generator import generate_days
from .layout import draw_page


def _digit_tag(cfg: SheetConfig) -> str:
    return "_".join(f"{a}x{b}" for a, b in cfg.digit_pairs)


def _resolve_target(cfg: SheetConfig, out_path: str | None, default_suffix: str) -> Path:
    if out_path:
        target = Path(out_path)
    elif cfg.out_path:
        target = Path(cfg.out_path)
    else:
        target = Path(default_output_path(cfg))
    if target.suffix.lower() != default_suffix:
        target = target.with_suffix(default_suffix)
    target.parent.mkdir(parents=True, exist_ok=True)
    return target


def _render_all(c: canvas.Canvas, cfg: SheetConfig) -> int:
    """把整批日期渲染进同一个 canvas，返回总页数（每天 cfg.pages 页）。"""
    days = generate_days(cfg)
    dates = cfg.date_list()
    total = sum(len(sheets) for sheets in days)

    page_no = 0
    for sheets, d in zip(days, dates):
        label = cfg.date_label(d)
        for problems in sheets:
            page_no += 1
            draw_page(c, cfg, problems, page_no, total, label)
            c.showPage()
    return total


def build_pdf(cfg: SheetConfig, out_path: str | None = None) -> str:
    """生成合并 PDF 并返回文件绝对路径。"""
    cfg.normalize()
    target = _resolve_target(cfg, out_path, ".pdf")

    c = canvas.Canvas(str(target), pagesize=(PAGE_WIDTH, PAGE_HEIGHT))
    c.setTitle(cfg.title)
    c.setAuthor("math-worksheet")
    _render_all(c, cfg)
    c.save()
    return str(target.resolve())


def build_pdf_bytes(cfg: SheetConfig) -> bytes:
    """生成合并 PDF 并以字节返回，供本地 Web UI 直接下载。"""
    cfg.normalize()
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(PAGE_WIDTH, PAGE_HEIGHT))
    c.setTitle(cfg.title)
    c.setAuthor("math-worksheet")
    _render_all(c, cfg)
    c.save()
    return buf.getvalue()


def _single_day_pdf_bytes(cfg: SheetConfig, sheets: list[list[tuple[int, int]]], label: str) -> bytes:
    """渲染某一天的独立 PDF（当天共 len(sheets) 页）。"""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(PAGE_WIDTH, PAGE_HEIGHT))
    c.setTitle(cfg.title)
    c.setAuthor("math-worksheet")
    total = len(sheets)
    for index, problems in enumerate(sheets, start=1):
        draw_page(c, cfg, problems, index, total, label)
        c.showPage()
    c.save()
    return buf.getvalue()


def build_zip_bytes(cfg: SheetConfig) -> bytes:
    """每天生成一个独立 PDF 并打包为 ZIP（题目跨天共享去重）。"""
    cfg.normalize()
    days = generate_days(cfg)
    dates = cfg.date_list()
    tag = _digit_tag(cfg)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for sheets, d in zip(days, dates):
            if not sheets:
                continue
            data = _single_day_pdf_bytes(cfg, sheets, cfg.date_label(d))
            zf.writestr(f"{cfg.title}_{tag}_{d.isoformat()}.pdf", data)
    return buf.getvalue()


def build_zip(cfg: SheetConfig, out_path: str | None = None) -> str:
    """生成每日独立 PDF 的 ZIP 包并返回文件绝对路径。"""
    cfg.normalize()
    target = _resolve_target(cfg, out_path, ".zip")
    target.write_bytes(build_zip_bytes(cfg))
    return str(target.resolve())


def build(cfg: SheetConfig, out_path: str | None = None) -> str:
    """按 cfg.output_mode 选择合并 PDF 或 ZIP 包。"""
    cfg.normalize()
    if cfg.output_mode == "zip":
        return build_zip(cfg, out_path)
    return build_pdf(cfg, out_path)


def suggested_filename(cfg: SheetConfig) -> str:
    """下载时的建议文件名。"""
    cfg.normalize()
    tag = _digit_tag(cfg)
    suffix = ".zip" if cfg.output_mode == "zip" else ".pdf"
    return f"{cfg.title}_{tag}_{date_range_tag(cfg)}{suffix}"


def open_in_explorer(path: str) -> None:
    """在文件管理器中定位生成的文件（Windows）。"""
    try:
        os.startfile(os.path.dirname(path))  # type: ignore[attr-defined]
    except Exception:
        pass
