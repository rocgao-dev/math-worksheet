# -*- coding: utf-8 -*-
"""UI 全链路冒烟测试：启动本地服务 -> GET 首页 -> POST /generate 取 PDF。

不调用 main()，因此不会弹出浏览器窗口。
"""
import http.server
import os
import sys
import threading
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import app_web  # noqa: E402

PORT = 8899

srv = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), app_web.Handler)
threading.Thread(target=srv.serve_forever, daemon=True).start()

try:
    html = urllib.request.urlopen("http://127.0.0.1:%d/" % PORT, timeout=10).read()
    print("GET /            -> %d bytes html, contains form: %s" % (len(html), b"generate" in html))

    params = [
        ("digits", "3"), ("digits", "4"),
        ("per_page", "9"), ("pages", "1"), ("columns", "2"),
        ("title", "UI smoke test"), ("date_str", "2026-10-08"),
        ("name", "on"), ("class", "on"), ("time", "on"), ("dedup", "on"),
        ("font_size", "14"),
    ]
    body = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request("http://127.0.0.1:%d/generate" % PORT, data=body)
    resp = urllib.request.urlopen(req, timeout=20)
    pdf = resp.read()
    print("POST /generate   -> status=%s type=%s size=%d header=%s"
          % (resp.status, resp.headers.get("Content-Type"), len(pdf), pdf[:5]))
    print("Content-Disposition:", resp.headers.get("Content-Disposition"))

    # 空位数应返回 400 并给出提示
    bad = urllib.request.Request("http://127.0.0.1:%d/generate" % PORT,
                                 data=urllib.parse.urlencode([("per_page", "5")]).encode())
    try:
        urllib.request.urlopen(bad, timeout=10)
        print("empty digits     -> UNEXPECTED success")
    except urllib.error.HTTPError as e:
        print("empty digits     -> HTTP %d (expected 400)" % e.code)
finally:
    srv.shutdown()

print("SMOKE OK" if pdf[:4] == b"%PDF" else "SMOKE FAILED")
