#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""本地 Web UI：浏览器中勾选参数，一键生成并下载 A4 练习题 PDF。

支持单日或日期区间批量出卷（可选只在指定星期出卷），输出合并 PDF 或打包 ZIP。
仅使用 Python 标准库（http.server）+ ReportLab，无需安装额外依赖。
运行后会自动打开浏览器；关闭命令行窗口即退出。
"""
from __future__ import annotations

import http.server
import sys
import threading
import urllib.parse
import webbrowser
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src.config import SheetConfig, parse_weekdays  # noqa: E402
from src.pdf_builder import build_pdf_bytes, build_zip_bytes, suggested_filename  # noqa: E402

DEFAULT_PORT = 8765


# ----------------------------------------------------------------- HTML 页面
def build_html() -> str:
    today = date.today().isoformat()
    end_default = (date.today() + timedelta(days=6)).isoformat()
    weekday_items = ""
    labels = (("mon", "周一"), ("tue", "周二"), ("wed", "周三"), ("thu", "周四"),
              ("fri", "周五"), ("sat", "周六"), ("sun", "周日"))
    for value, text in labels:
        weekday_items += (
            f'<label class="check"><input type="checkbox" name="weekdays" value="{value}">{text}</label>'
        )

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>乘法计算练习题生成器</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  :root {{ --brand:#2563eb; --line:#e5e7eb; --bg:#f6f7f9; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; padding:32px 16px; background:var(--bg); color:#111827;
         font-family:"Microsoft YaHei","PingFang SC",system-ui,sans-serif; }}
  .card {{ max-width:760px; margin:0 auto; background:#fff; border:1px solid var(--line);
           border-radius:14px; padding:28px 32px 32px; box-shadow:0 6px 24px rgba(0,0,0,.06); }}
  h1 {{ margin:0 0 6px; font-size:22px; }}
  .sub {{ color:#6b7280; font-size:13px; margin-bottom:22px; }}
  fieldset {{ border:1px solid var(--line); border-radius:10px; padding:14px 16px 16px; margin:0 0 18px; }}
  legend {{ padding:0 6px; font-size:13px; color:#374151; font-weight:600; }}
  .row {{ display:flex; gap:18px; flex-wrap:wrap; }}
  .field {{ display:flex; flex-direction:column; gap:6px; margin-bottom:4px; }}
  .field label {{ font-size:13px; color:#374151; }}
  input[type=text],input[type=number],input[type=date] {{
      padding:8px 10px; border:1px solid var(--line); border-radius:8px; font-size:14px; width:100%; }}
  .check {{ display:inline-flex; align-items:center; gap:6px; font-size:14px; margin:2px 16px 2px 0; cursor:pointer; }}
  .check input {{ width:16px; height:16px; accent-color:var(--brand); }}
  .radio {{ display:inline-flex; align-items:center; gap:6px; font-size:14px; margin:2px 20px 2px 0; cursor:pointer; }}
  .radio input {{ width:16px; height:16px; accent-color:var(--brand); }}
  .hint {{ color:#9ca3af; font-size:12px; margin-top:6px; }}
  .box {{ margin-top:12px; padding:12px 14px; background:#f9fafb; border:1px dashed var(--line); border-radius:10px; }}
  button {{ margin-top:6px; width:100%; padding:13px; border:0; border-radius:10px; background:var(--brand);
            color:#fff; font-size:16px; font-weight:600; cursor:pointer; }}
  button:hover {{ background:#1d4ed8; }}
  #msg {{ margin-top:12px; font-size:14px; color:#b91c1c; white-space:pre-wrap; }}
</style>
</head>
<body>
<div class="card">
  <h1>乘法计算练习题生成器</h1>
  <div class="sub">A4 纵向 · 打印即用 · 可一次生成多天 · 本地离线生成，题目不会上传</div>

  <form id="f" method="post" action="/generate">
    <fieldset>
      <legend>乘数位数（可多选，选中即混合出题）</legend>
      <label class="check"><input type="checkbox" name="digits" value="3">三位数 × 三位数</label>
      <label class="check"><input type="checkbox" name="digits" value="4" checked>四位数 × 四位数</label>
      <label class="check"><input type="checkbox" name="digits" value="5">五位数 × 五位数</label>
      <div class="hint">按位数区间随机取数（三位数 = 100–999）；配合“严格数字规则”时不含 0/1、各位不重复、相邻不连号。</div>
    </fieldset>

    <fieldset>
      <legend>日期与批量</legend>
      <label class="radio"><input type="radio" name="date_mode" value="single" checked>单日</label>
      <label class="radio"><input type="radio" name="date_mode" value="range">日期区间（一次生成多天）</label>

      <div class="box" id="single-box">
        <div class="field" style="max-width:220px">
          <label>日期</label>
          <input type="date" name="date_str" value="{today}">
        </div>
      </div>

      <div class="box" id="range-box" style="display:none">
        <div class="row">
          <div class="field" style="flex:1 1 180px">
            <label>起始日期</label>
            <input type="date" name="date_start" value="{today}">
          </div>
          <div class="field" style="flex:1 1 180px">
            <label>结束日期</label>
            <input type="date" name="date_end" value="{end_default}">
          </div>
        </div>
        <div style="margin-top:10px">
          <label style="font-size:13px;color:#374151">只在指定星期出卷（不选 = 区间内每天都出）</label><br>
          {weekday_items}
        </div>
        <div class="hint">例：区间 10-09 至 10-31 且只勾“周一/周三/周五”，就只出这些天的试卷。</div>
      </div>

      <div style="margin-top:12px">
        <label class="check"><input type="checkbox" name="show_weekday" checked>页眉日期显示星期（如 2026-10-09（周五））</label>
      </div>
    </fieldset>

    <fieldset>
      <legend>版面</legend>
      <div class="row">
        <div class="field" style="flex:1 1 130px">
          <label>每页题数</label>
          <input type="number" name="per_page" value="6" min="1" max="60">
        </div>
        <div class="field" style="flex:1 1 130px">
          <label>每天页数</label>
          <input type="number" name="pages" value="1" min="1" max="50">
        </div>
        <div class="field" style="flex:1 1 130px">
          <label>列数</label>
          <input type="number" name="columns" value="2" min="1" max="5">
        </div>
        <div class="field" style="flex:1 1 130px">
          <label>题面字号(pt)</label>
          <input type="number" name="font_size" value="14" min="9" max="28">
        </div>
      </div>
      <div class="hint">题量较多时会自动缩小字号以适配 A4；大数乘法建议每页 6–12 题，留足竖式空间。</div>
    </fieldset>

    <fieldset>
      <legend>卷头信息</legend>
      <div class="row">
        <div class="field" style="flex:2 1 240px">
          <label>标题</label>
          <input type="text" name="title" value="乘法计算练习">
        </div>
      </div>
      <div style="margin-top:8px">
        <label class="check"><input type="checkbox" name="name" checked>姓名栏</label>
        <label class="check"><input type="checkbox" name="class" checked>班级栏</label>
        <label class="check"><input type="checkbox" name="time" checked>用时栏</label>
        <label class="check"><input type="checkbox" name="score" checked>得分栏</label>
      </div>
    </fieldset>

    <fieldset>
      <legend>输出与生成选项</legend>
      <label class="radio"><input type="radio" name="output_mode" value="merge" checked>合并成一个 PDF</label>
      <label class="radio"><input type="radio" name="output_mode" value="zip">打包成 ZIP（每天一个 PDF）</label>
      <div style="margin-top:10px">
        <label style="font-size:13px;color:#374151">题目去重范围</label><br>
        <label class="radio"><input type="radio" name="dedup_mode" value="page" checked>同一天内不重复（跨天、跨页可重复）</label>
        <label class="radio"><input type="radio" name="dedup_mode" value="sheet">整份试卷都不重复</label>
        <label class="radio"><input type="radio" name="dedup_mode" value="none">不去重</label>
      </div>
      <div style="margin-top:10px">
        <label class="check"><input type="checkbox" name="strict" checked>严格数字规则（不含 0 和 1 · 各位数字不重复 · 相邻不连号）</label>
      </div>
      <div class="field" style="margin-top:10px;max-width:220px">
        <label>随机种子（选填，填数字可复现同一批题目）</label>
        <input type="number" name="seed" placeholder="留空则每次随机">
      </div>
    </fieldset>

    <button type="submit">生成并下载</button>
    <div id="msg"></div>
  </form>
</div>
<script>
function syncMode() {{
  var m = document.querySelector('input[name=date_mode]:checked').value;
  document.getElementById('single-box').style.display = (m === 'single') ? '' : 'none';
  document.getElementById('range-box').style.display = (m === 'range') ? '' : 'none';
}}
document.querySelectorAll('input[name=date_mode]').forEach(function (el) {{
  el.addEventListener('change', syncMode);
}});
syncMode();

document.getElementById('f').addEventListener('submit', function (e) {{
  var msg = document.getElementById('msg');
  var digits = document.querySelectorAll('input[name=digits]:checked');
  if (digits.length === 0) {{
    e.preventDefault();
    msg.textContent = '请至少勾选一种乘数位数。';
    return;
  }}
  var mode = document.querySelector('input[name=date_mode]:checked').value;
  if (mode === 'range') {{
    var s = document.querySelector('input[name=date_start]').value;
    var t = document.querySelector('input[name=date_end]').value;
    if (!s || !t) {{
      e.preventDefault();
      msg.textContent = '日期区间需要填写起始日期和结束日期。';
      return;
    }}
  }}
  msg.textContent = '正在生成，请稍候…';
  msg.style.color = '#2563eb';
}});
</script>
</body>
</html>
"""


# ----------------------------------------------------------------- 表单解析
def parse_form(form: dict[str, list[str]]) -> SheetConfig:
    def one(key: str, default: str = "") -> str:
        values = form.get(key)
        return values[0] if values else default

    digits = [int(v) for v in form.get("digits", []) if v.strip().isdigit()]
    if not digits:
        raise ValueError("请至少勾选一种乘数位数（三位数 / 四位数 / 五位数）")

    mode = one("date_mode", "single")
    if mode == "range":
        date_start = one("date_start").strip() or date.today().isoformat()
        date_end = one("date_end").strip()
        if not date_end:
            raise ValueError("日期区间需要填写结束日期")
        weekdays = parse_weekdays(",".join(form.get("weekdays", [])))
    else:
        date_start = one("date_str").strip() or date.today().isoformat()
        date_end = ""
        weekdays = ()

    seed_text = one("seed").strip()
    dedup_mode = one("dedup_mode", "page")
    cfg = SheetConfig(
        digit_pairs=tuple((d, d) for d in digits),
        problems_per_page=int(one("per_page", "6") or 6),
        pages=int(one("pages", "1") or 1),
        columns=int(one("columns", "2") or 2),
        title=(one("title").strip() or "乘法计算练习"),
        date_str=date_start,
        date_end=date_end,
        weekdays=weekdays,
        show_weekday="show_weekday" in form,
        output_mode=one("output_mode", "merge"),
        show_name="name" in form,
        show_class="class" in form,
        show_time="time" in form,
        show_score="score" in form,
        dedup=dedup_mode != "none",
        dedup_scope="sheet" if dedup_mode == "sheet" else "page",
        strict_digits="strict" in form,
        seed=int(seed_text) if seed_text else None,
        font_size=int(one("font_size", "14") or 14),
    )
    return cfg.normalize()


# ----------------------------------------------------------------- HTTP 服务
class Handler(http.server.BaseHTTPRequestHandler):
    server_version = "MathWorksheet/1.0"

    def log_message(self, fmt: str, *args) -> None:  # 静默，保持控制台干净
        pass

    def _send(self, code: int, body: bytes, content_type: str, extra: dict | None = None) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path in ("/", "/index.html"):
            self._send(200, build_html().encode("utf-8"), "text/html; charset=utf-8")
        else:
            self._send(404, "404 Not Found".encode("utf-8"), "text/plain; charset=utf-8")

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/generate":
            self._send(404, "404 Not Found".encode("utf-8"), "text/plain; charset=utf-8")
            return

        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length).decode("utf-8", errors="replace")
        form = urllib.parse.parse_qs(raw, keep_blank_values=True)

        try:
            cfg = parse_form(form)
            if cfg.output_mode == "zip":
                data = build_zip_bytes(cfg)
                content_type = "application/zip"
            else:
                data = build_pdf_bytes(cfg)
                content_type = "application/pdf"
            filename = suggested_filename(cfg)
            quoted = urllib.parse.quote(filename)
            self._send(
                200,
                data,
                content_type,
                {"Content-Disposition": f"attachment; filename=\"sheet\"; filename*=UTF-8''{quoted}"},
            )
        except Exception as exc:  # 参数错误等回显给用户
            html = (
                "<!DOCTYPE html><html lang='zh-CN'><meta charset='utf-8'>"
                f"<body style='font-family:Microsoft YaHei;padding:40px'><h3>生成失败</h3>"
                f"<p style='color:#b91c1c'>{exc}</p>"
                "<p><a href='/'>返回修改参数</a></p></body></html>"
            )
            self._send(400, html.encode("utf-8"), "text/html; charset=utf-8")


class WorksheetServer(http.server.ThreadingHTTPServer):
    """Windows 默认的 SO_REUSEADDR 允许多个进程绑定同一端口，

    会造成“重复启动后仍由旧实例响应页面”的假象；
    关闭它，使端口冲突真正抛错并自动顺延到下一端口。
    """

    allow_reuse_address = False


def main() -> int:
    port = DEFAULT_PORT
    server = None
    for candidate in range(DEFAULT_PORT, DEFAULT_PORT + 20):
        try:
            server = WorksheetServer(("127.0.0.1", candidate), Handler)
            port = candidate
            break
        except OSError:
            continue

    if server is None:
        print("[ERROR] 端口 8765-8784 均被占用，无法启动本地 UI。")
        return 1

    url = f"http://127.0.0.1:{port}/"
    print("=" * 56)
    print("  乘法计算练习题生成器（本地 UI）已启动")
    print(f"  地址：{url}")
    print("  浏览器会自动打开；关闭本窗口即退出程序。")
    print("=" * 56)

    threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已退出。")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
