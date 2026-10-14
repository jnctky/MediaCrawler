# -*- coding: utf-8 -*-
"""根据 _report_data_*.json 生成 HTML 可视化报告（零外部依赖，双击即看）
用法：python _build_html.py            # 自动用最新的 _report_data_*.json
      python _build_html.py --data xxx.json --out yyy.html
"""
import json, os, html, glob, argparse, sys, io, re

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
_THIS = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(_THIS), "报告")   # 仓库根下的 报告/ 目录


def esc(s):
    return html.escape(str(s if s is not None else ""))


def pick():
    fs = [p for p in glob.glob(os.path.join(OUT, "_report_data_*.json"))]
    if not fs:
        return None
    return max(fs, key=os.path.getmtime)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--title", default=None)
    args = ap.parse_args()

    dp = args.data or pick()
    if not dp:
        print("找不到 _report_data_*.json"); return
    d = json.load(open(dp, encoding="utf-8"))

    label = d.get("label", "未标注")
    title = args.title or f"小红书抓取结果报告 · {label}"

    mx = max((n["liked"] for n in d["top_notes"]), default=1) or 1

    rows = []
    for i, n in enumerate(d["top_notes"], 1):
        pct = n["liked"] / mx * 100
        tags = "".join(f'<span class="tg">#{esc(t)}</span>' for t in n["tags"])
        rows.append(f"""
    <div class="brow">
      <div class="brank">{i}</div>
      <div class="bbody">
        <a class="btitle" href="{esc(n['url'])}" target="_blank">{esc(n['title'])}</a>
        <div class="bmeta">
          <span class="pill {'v' if n['type']=='视频' else 'n'}">{esc(n['type'])}</span>
          <span>赞 <b class="num">{n['liked']:,}</b></span>
          <span>藏 {n['collected']:,}</span>
          <span>评 {n['comment']:,}</span>
          <span>转 {n['share']:,}</span>
          <span class="dim">{esc(n['date'])}</span>
        </div>
        <div class="btrack"><div class="bfill" style="width:{pct:.1f}%"></div></div>
        <div class="btags">{tags}</div>
      </div>
    </div>""")

    kwc = []
    for k in d.get("kw_stats", []):
        kwc.append(f"""
    <div class="kwcard">
      <div class="kwhead"><span class="kwname">#{esc(k['kw'])}</span><span class="kwn">{k['count']} 篇</span></div>
      <div class="kwgrid">
        <div><span class="kl">最高赞</span><span class="kv hot">{k['max']:,}</span></div>
        <div><span class="kl">中位赞</span><span class="kv">{int(k['median']):,}</span></div>
        <div><span class="kl">均值赞</span><span class="kv">{k['mean']:,}</span></div>
        <div><span class="kl">破千篇</span><span class="kv">{k['over1000']}</span></div>
        <div><span class="kl">破万篇</span><span class="kv">{k.get('over10000',0)}</span></div>
        <div><span class="kl">平均收藏</span><span class="kv">{k['avg_col']:,}</span></div>
        <div><span class="kl">视频占比</span><span class="kv">{k['video_pct']}%</span></div>
      </div>
    </div>""")

    typebars = []
    if d.get("note_type_like"):
        tm = max(v["mean"] for v in d["note_type_like"].values()) or 1
        for lab, v in d["note_type_like"].items():
            typebars.append(f"""
        <div class="tb">
          <div class="tbhead"><span>{esc(lab)}（{v['n']} 篇）</span><span class="num">均值 {v['mean']:,}</span></div>
          <div class="btrack"><div class="bfill {'v' if lab=='视频' else 'n'}" style="width:{v['mean']/tm*100:.1f}%"></div></div>
        </div>""")

    chips = []
    tags = d.get("tags", [])
    tmax = max((t["count"] for t in tags), default=1) or 1
    for t in tags:
        sz = 12 + (t["count"] / tmax) * 12
        op = 0.45 + (t["count"] / tmax) * 0.55
        chips.append(f'<span class="chip" style="font-size:{sz:.1f}px;opacity:{op:.2f}">#{esc(t["name"])}<i>{t["count"]}</i></span>')

    cmts = []
    for i, c in enumerate(d.get("top_cmts", []), 1):
        cmts.append(f'<li><span class="crank">{i}</span><p>{esc(c["content"])}</p><span class="clike">♥ {c["like"]:,}</span></li>')

    # 点赞分布
    lks = d.get("all_liked", [])
    bins = [(0, 1000), (1000, 5000), (5000, 10000), (10000, 50000), (50000, 100000), (100000, 10**9)]
    bh = [sum(1 for x in lks if a <= x < b) for a, b in bins]
    bmax = max(bh) or 1
    hist = "".join(
        f'<div class="hbar"><span class="hlab">{a:,}-{"10万+" if b>10**8 else format(b, ",")}</span>'
        f'<div class="htrack"><div class="hfill" style="width:{c/bmax*100:.0f}%"></div></div>'
        f'<span class="hval">{c} 篇</span></div>'
        for (a, b), c in zip(bins, bh))

    # 时间分布（按月）
    th = d.get("time_hist", {})
    tline = ""
    if th:
        vmax = max(th.values()) or 1
        bars = "".join(
            f'<div class="mcol" title="{esc(k)}: {v} 篇"><div class="mbar" style="height:{max(v/vmax*90,4):.0f}%"></div><span class="mlab">{esc(k[2:])}</span></div>'
            for k, v in th.items())
        tline = f'<div class="mchart">{bars}</div>'

    ls = d["like_stats"]
    doc = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font:14px/1.6 -apple-system,"Segoe UI","微软雅黑",sans-serif;background:#F7F8FA;color:#1F2329;padding:28px 18px 60px}}
.wrap{{max-width:1080px;margin:0 auto}}
.hero{{background:linear-gradient(135deg,#FF2442,#FF6B4A);border-radius:16px;padding:28px 30px;color:#fff;box-shadow:0 8px 24px rgba(255,36,66,.22)}}
.hero h1{{font-size:24px;font-weight:700}}
.hero .sub{{margin-top:8px;opacity:.92;font-size:13px}}
.hero .src{{margin-top:14px;font-size:12px;opacity:.8;font-family:ui-monospace,Consolas,monospace}}
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:14px;margin:20px 0}}
.card{{background:#fff;border-radius:12px;padding:16px 18px;border:1px solid #EDEFF2}}
.card .k{{font-size:12px;color:#8A9099}}
.card .v{{font-size:26px;font-weight:700;margin-top:6px;letter-spacing:-.5px}}
.card .v.red{{color:#FF2442}}
.card .d{{font-size:11px;color:#A8AEB6;margin-top:2px}}
h2{{font-size:16px;font-weight:700;margin:30px 0 14px;padding-left:11px;border-left:4px solid #FF2442}}
.panel{{background:#fff;border:1px solid #EDEFF2;border-radius:12px;padding:18px 20px}}
.brow{{display:flex;gap:14px;padding:13px 0;border-bottom:1px dashed #EDEFF2}}
.brow:last-child{{border-bottom:0}}
.brank{{flex:0 0 26px;height:26px;border-radius:8px;background:#F2F3F5;color:#6B7280;font-weight:700;font-size:12px;display:flex;align-items:center;justify-content:center}}
.brow:nth-child(1) .brank{{background:#FF2442;color:#fff}}
.brow:nth-child(2) .brank{{background:#FF7A5C;color:#fff}}
.brow:nth-child(3) .brank{{background:#FFB199;color:#fff}}
.bbody{{flex:1;min-width:0}}
.btitle{{color:#1F2329;font-weight:600;text-decoration:none;font-size:14px}}
.btitle:hover{{color:#FF2442}}
.bmeta{{display:flex;flex-wrap:wrap;gap:12px;font-size:12px;color:#6B7280;margin-top:6px;align-items:center}}
.num{{color:#FF2442;font-weight:700}}
.btrack{{height:6px;background:#F2F3F5;border-radius:4px;margin-top:8px;overflow:hidden}}
.bfill{{height:100%;border-radius:4px;background:linear-gradient(90deg,#FF2442,#FF6B4A)}}
.bfill.v{{background:linear-gradient(90deg,#FF2442,#FF8A5C)}}
.bfill.n{{background:linear-gradient(90deg,#4B7BFF,#7EA6FF)}}
.btags{{margin-top:7px;display:flex;flex-wrap:wrap;gap:6px}}
.tg{{font-size:11px;color:#8A9099;background:#F5F6F7;border-radius:5px;padding:1px 7px}}
.pill{{font-size:11px;padding:1px 7px;border-radius:5px;font-weight:600}}
.pill.v{{background:#FFEBEE;color:#FF2442}}
.pill.n{{background:#EAF0FF;color:#3B6BFF}}
.dim{{color:#A8AEB6}}
.kwcard{{background:#fff;border:1px solid #EDEFF2;border-radius:12px;padding:16px 18px}}
.kwcard + .kwcard{{margin-top:12px}}
.kwhead{{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:12px}}
.kwname{{font-size:15px;font-weight:700;color:#FF2442}}
.kwn{{font-size:12px;color:#8A9099}}
.kwgrid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(100px,1fr));gap:12px}}
.kl{{display:block;font-size:11px;color:#8A9099}}
.kv{{font-size:16px;font-weight:700}}
.kv.hot{{color:#FF2442}}
.tb + .tb{{margin-top:14px}}
.tbhead{{display:flex;justify-content:space-between;font-size:13px;margin-bottom:6px}}
.chips{{display:flex;flex-wrap:wrap;gap:9px;align-items:center}}
.chip{{background:#FFF0F2;color:#D91E38;border:1px solid #FFD6DC;border-radius:20px;padding:4px 12px;font-weight:600;white-space:nowrap}}
.chip i{{font-style:normal;opacity:.6;font-size:11px;margin-left:5px}}
.cmts{{list-style:none}}
.cmts li{{display:flex;gap:12px;align-items:flex-start;padding:12px 0;border-bottom:1px dashed #EDEFF2}}
.cmts li:last-child{{border-bottom:0}}
.crank{{flex:0 0 22px;height:22px;border-radius:6px;background:#F2F3F5;color:#6B7280;font-size:11px;font-weight:700;display:flex;align-items:center;justify-content:center}}
.cmts p{{flex:1;font-size:13px;color:#3D4450;min-width:0}}
.clike{{flex:0 0 auto;font-size:12px;color:#FF2442;font-weight:700}}
.hbar{{display:flex;align-items:center;gap:12px;margin-bottom:10px}}
.hlab{{flex:0 0 96px;font-size:12px;color:#6B7280;text-align:right}}
.htrack{{flex:1;height:20px;background:#F5F6F7;border-radius:5px;overflow:hidden}}
.hfill{{height:100%;background:linear-gradient(90deg,#FF8A5C,#FF2442);border-radius:5px}}
.hval{{flex:0 0 46px;font-size:12px;color:#3D4450;font-weight:600}}
.mchart{{display:flex;align-items:flex-end;gap:6px;height:130px;padding-top:10px;overflow-x:auto}}
.mcol{{flex:0 0 auto;width:38px;display:flex;flex-direction:column;align-items:center;height:100%;justify-content:flex-end}}
.mbar{{width:100%;background:linear-gradient(180deg,#FF2442,#FF8A5C);border-radius:4px 4px 0 0;min-height:3px}}
.mlab{{font-size:10px;color:#8A9099;margin-top:5px;white-space:nowrap}}
.foot{{margin-top:36px;padding-top:18px;border-top:1px solid #EDEFF2;font-size:12px;color:#8A9099;line-height:1.9}}
.foot code{{background:#F5F6F7;padding:1px 6px;border-radius:4px;font-family:ui-monospace,Consolas,monospace;color:#D91E38}}
</style>
</head>
<body>
<div class="wrap">

  <div class="hero">
    <h1>小红书抓取结果报告 · {esc(label)}</h1>
    <div class="sub">关键词：{' · '.join('<b>'+esc(k)+'</b>' for k in d.get('keywords',[]))}　|　采集工具：MediaCrawler（本地自建）</div>
    <div class="src">数据源：{esc(' ・ '.join(d.get('source_files',[])))}<br>
    生成时间：{esc(d['generated_at'])}　|　笔记发布时间跨度：{esc(d.get('time_span',''))}</div>
  </div>

  <div class="cards">
    <div class="card"><div class="k">有效笔记</div><div class="v">{d['notes']}</div><div class="d">原始 {d['raw_notes']} 条，已去重</div></div>
    <div class="card"><div class="k">有效评论</div><div class="v">{d['cmts']}</div><div class="d">原始 {d['raw_cmts']} 条，已去重</div></div>
    <div class="card"><div class="k">最高点赞</div><div class="v red">{ls['max']:,}</div><div class="d">中位 {int(ls['median']):,} / 均值 {ls['mean']:,}</div></div>
    <div class="card"><div class="k">破万赞笔记</div><div class="v">{ls.get('over10000',0)}</div><div class="d">破千 {ls['over1000']} 篇</div></div>
    <div class="card"><div class="k">内容形态</div><div class="v">{d['type_dist'].get('图文',0)}<span style="font-size:15px;color:#8A9099"> 图文 / {d['type_dist'].get('视频',0)} 视频</span></div><div class="d">按笔记数统计</div></div>
  </div>

  <h2>一、爆款笔记（按点赞排序，最多展示 30 篇）</h2>
  <div class="panel">{''.join(rows)}</div>

  <h2>二、点赞量分布</h2>
  <div class="panel">{hist}</div>

  <h2>三、发布时间分布（按月）</h2>
  <div class="panel">{tline or '<span style="color:#8A9099">无时间数据</span>'}</div>

  <h2>四、关键词表现对比</h2>
  {''.join(kwc) or '<div class="panel" style="color:#8A9099">无</div>'}

  <h2>五、图文 vs 视频：平均点赞</h2>
  <div class="panel">{''.join(typebars) or '<span style="color:#8A9099">无</span>'}</div>

  <h2>六、话题标签热度</h2>
  <div class="panel"><div class="chips">{''.join(chips)}</div></div>

  <h2>七、高热评论 Top 10</h2>
  <div class="panel"><ul class="cmts">{''.join(cmts) or '<li style="color:#8A9099">未抓取评论</li>'}</ul></div>

  <div class="foot">
    <b>怎么看：</b>笔记标题可点击跳转原文；数据可回溯到配套 Excel <code>MediaCrawler-小红书抓取报告_{esc(label)}.xlsx</code>。<br>
    <b>口径说明：</b>点赞/收藏等为抓取时刻快照；爆款笔记的原始值可能是「10万+」这类上限显示，报表中按 10 万计。<br>
    <b>合规提醒：</b>本数据仅供个人学习研究，请勿商用或二次分发。
  </div>

</div>
</body>
</html>"""

    safe_label = re.sub(r'[\\/:*?"<>|]', "_", label)
    out = args.out or os.path.join(OUT, "小红书抓取结果报告_" + safe_label + ".html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(doc)
    print("HTML:", out, f"({os.path.getsize(out)/1024:.1f} KB)")


if __name__ == "__main__":
    main()
