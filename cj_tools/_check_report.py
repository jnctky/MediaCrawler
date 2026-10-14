# -*- coding: utf-8 -*-
"""无头渲染报告 HTML，检查元素与报错，并截图
用法：python _check_report.py "报告\小红书抓取结果报告_手账.html"
"""
import asyncio, sys, os, io
from playwright.async_api import async_playwright

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

_THIS = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(_THIS)               # MediaCrawler 仓库根
rel = sys.argv[1] if len(sys.argv) > 1 else os.path.join("报告", "小红书抓取结果报告.html")
path = rel if os.path.isabs(rel) else os.path.join(REPO, rel)
URL = "file:///" + path.replace("\\", "/").replace(" ", "%20")
SHOT = os.path.join(os.path.dirname(path), os.path.splitext(os.path.basename(path))[0] + "-preview.png")


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={"width": 1160, "height": 1400}, device_scale_factor=1.5)
        errs = []
        pg.on("console", lambda m: errs.append(f"[{m.type}] {m.text}") if m.type == "error" else None)
        pg.on("pageerror", lambda e: errs.append(f"[pageerror] {e}"))
        await pg.goto(URL, wait_until="load")
        await pg.wait_for_timeout(1200)

        checks = {
            "标题": await pg.title(),
            "卡片": await pg.locator(".card").count(),
            "爆款条目": await pg.locator(".brow").count(),
            "标签": await pg.locator(".chip").count(),
            "热评": await pg.locator(".cmts li").count(),
            "分布条": await pg.locator(".hbar").count(),
            "月份柱": await pg.locator(".mcol").count(),
            "最高赞": await pg.locator(".card .v.red").first.inner_text(),
            "正文可见": await pg.locator(".hero h1").is_visible(),
        }
        for k, v in checks.items():
            print(f"  {k}: {v}")
        print("  页面高度:", await pg.evaluate("document.body.scrollHeight"), "px")
        print("  JS 错误:", errs if errs else "无 ✅")
        await pg.screenshot(path=SHOT, full_page=True)
        print("  截图:", SHOT)
        await b.close()

asyncio.run(main())
