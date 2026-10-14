# -*- coding: utf-8 -*-
"""无头浏览器渲染 MediaCrawler WebUI，捕获控制台错误并截图。"""
import os
import sys
from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:8090/"
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # MediaCrawler 仓库根
OUT = os.path.join(REPO, "报告", "webui-check.png")

logs = []
errors = []

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 950})
    page.on("console", lambda m: logs.append(f"[{m.type}] {m.text}"))
    page.on("pageerror", lambda e: errors.append(str(e)))
    failed = []
    page.on("requestfailed", lambda r: failed.append(f"{r.url} -> {r.failure}"))

    page.goto(URL, wait_until="networkidle", timeout=60000)
    page.wait_for_timeout(3000)

    title = page.title()
    root_len = len(page.inner_html("#root"))
    body_text = page.inner_text("body")[:600]

    page.screenshot(path=OUT, full_page=False)
    browser.close()

print("=" * 60)
print("标题:", title)
print("#root 渲染出的 HTML 长度:", root_len, "(>500 表示页面确实渲染出了内容)")
print("=" * 60)
print("--- 页面可见文本(前 600 字) ---")
print(body_text)
print("=" * 60)
print("--- pageerror (JS 未捕获异常) ---")
print("\n".join(errors) if errors else "(无)")
print("--- 请求失败 ---")
print("\n".join(failed) if failed else "(无)")
print("--- 控制台 ---")
print("\n".join(logs[:40]) if logs else "(无)")
print("=" * 60)
print("截图:", OUT)
sys.exit(0)
