# -*- coding: utf-8 -*-
"""
MediaCrawler 抓取结果 —— 按发布时间过滤（本地筛，无需重跑爬虫）

用法示例：
  # 最近 90 天
  python xhs_time_filter.py --days 90

  # 指定区间
  python xhs_time_filter.py --since 2026-01-01 --until 2026-06-30

  # 指定输入文件
  python xhs_time_filter.py --input "MediaCrawler/data/xhs/json/*.json" --days 30

说明：
  - 自动兼容 json（一个数组）和 jsonl（每行一条）两种落盘格式
  - 自动去重（笔记按 note_id，评论按 comment_id）
  - 笔记与评论分别输出，互不混淆
  - 时间字段：笔记用 `time`，评论用 `create_time`（毫秒时间戳）
"""
import argparse, glob, json, os, sys, io, datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

_THIS = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(_THIS)               # MediaCrawler 仓库根
DEFAULT_GLOB = os.path.join(REPO, "data", "**", "*.json*")
DEFAULT_OUTDIR = os.path.join(REPO, "报告")


def load_records(paths):
    out, stat = [], []
    for p in paths:
        name = os.path.basename(p)
        # 跳过自产出的过滤结果，避免递归读入
        if name.startswith("filtered_"):
            continue
        if not os.path.isfile(p) or p.endswith(".lock"):
            continue
        try:
            with open(p, encoding="utf-8") as f:
                txt = f.read().strip()
            if not txt:
                continue
            if txt[0] == "[":
                data = json.loads(txt)
                recs = data if isinstance(data, list) else [data]
            else:
                recs = [json.loads(ln) for ln in txt.splitlines() if ln.strip()]
            out.extend(recs)
            stat.append((p, len(recs)))
        except Exception as e:
            print(f"  [跳过] {p}: {type(e).__name__} {e}")
    return out, stat


def get_ts(r):
    for k in ("time", "create_time", "last_modify_ts"):
        v = r.get(k)
        if v:
            try:
                return int(v)
            except Exception:
                pass
    return None


def is_comment(r):
    return "comment_id" in r


def dedup(recs):
    seen, out = set(), []
    for r in recs:
        k = r.get("comment_id") or ("N:" + str(r.get("note_id") or id(r)))
        if k in seen:
            continue
        seen.add(k); out.append(r)
    return out


def main():
    ap = argparse.ArgumentParser(description="按发布时间过滤 MediaCrawler 抓取结果")
    ap.add_argument("--input", default=DEFAULT_GLOB, help="输入文件，支持通配符")
    ap.add_argument("--days", type=int, help="只要最近 N 天")
    ap.add_argument("--since", help="起始日期 YYYY-MM-DD（含）")
    ap.add_argument("--until", help="结束日期 YYYY-MM-DD（含）")
    ap.add_argument("--outdir", default=DEFAULT_OUTDIR, help="输出目录")
    args = ap.parse_args()

    paths = sorted(glob.glob(args.input, recursive=True))
    if not paths:
        print("没匹配到文件:", args.input); return

    recs, stat = load_records(paths)
    if not recs:
        print("没读到任何记录"); return

    print("=== 输入 ===")
    for p, n in stat:
        print(f"  {n:>5} 条  {p}")
    print(f"  合计 {len(recs)} 条")

    before = len(recs)
    recs = dedup(recs)
    print(f"  去重后 {len(recs)} 条" + (f"（去掉 {before-len(recs)} 条重复）" if before != len(recs) else ""))

    now = datetime.datetime.now()
    lo = hi = None
    desc = []
    if args.days is not None:
        lo = now - datetime.timedelta(days=args.days); desc.append(f"最近 {args.days} 天")
    if args.since:
        lo = datetime.datetime.strptime(args.since, "%Y-%m-%d"); desc.append(f">= {args.since}")
    if args.until:
        hi = datetime.datetime.strptime(args.until, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
        desc.append(f"<= {args.until}")

    def keep(items):
        if lo is None and hi is None:
            return items
        out = []
        for r in items:
            t = get_ts(r)
            if t is None: continue
            d = datetime.datetime.fromtimestamp(t / 1000)
            if lo and d < lo: continue
            if hi and d > hi: continue
            out.append(r)
        return out

    notes = [r for r in recs if not is_comment(r)]
    cmts = [r for r in recs if is_comment(r)]
    kn, kc = keep(notes), keep(cmts)

    label = " 且 ".join(desc) if desc else "未指定（输出全部）"
    print(f"\n=== 过滤条件：{label} ===")

    os.makedirs(args.outdir, exist_ok=True)
    stamp = f"{now:%Y%m%d_%H%M}"
    written = []

    for items, kind, fn in [(kn, "笔记", f"filtered_notes_{stamp}.jsonl"),
                            (kc, "评论", f"filtered_comments_{stamp}.jsonl")]:
        tot = len(notes) if kind == "笔记" else len(cmts)
        ts = sorted(get_ts(r) for r in items if get_ts(r))
        span = ""
        if ts:
            a = datetime.datetime.fromtimestamp(ts[0]/1000); b = datetime.datetime.fromtimestamp(ts[-1]/1000)
            span = f"  跨度 {a:%Y-%m-%d} ~ {b:%Y-%m-%d}"
        print(f"  {kind}: {tot} -> {len(items)} 条{span}")
        if items:
            p = os.path.join(args.outdir, fn)
            with open(p, "w", encoding="utf-8") as f:
                for r in items:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
            written.append(p)

    if written:
        print("\n已写出：")
        for p in written:
            print("  " + p)
    else:
        print("\n过滤后为空，可放宽条件。")


if __name__ == "__main__":
    main()
