# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/api/services/time_filter.py
# GitHub: https://github.com/NanmiCoder
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1
#
# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：
# 1. 不得用于任何商业用途。
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。
# 3. 不得进行大规模爬取或对平台造成运营干扰。
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。
# 5. 不得用于任何非法或不当的用途。
#
# 详细许可条款请参阅项目根目录下的LICENSE文件。
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。

"""Post-crawl local time-range filter.

The crawler itself has no publish-time filter (the platform search API only
offers coarse ranges), so the WebUI offers a local filter that runs after a
crawl finishes. It never touches the original data files: filtered records are
written as separate ``filtered_*.json`` files under ``data/<platform>/filtered/``.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"

# Timestamp fields used by the different stores (millisecond epoch)
TIME_KEYS: Tuple[str, ...] = ("time", "create_time", "last_modify_ts")

# Files produced by this module are skipped when scanning, so re-running the
# filter never feeds on its own output.
OUTPUT_PREFIX = "filtered_"

DATE_FORMAT = "%Y-%m-%d"


def parse_date(value: str, end_of_day: bool = False) -> datetime:
    """Parse a ``YYYY-MM-DD`` string into a datetime."""
    parsed = datetime.strptime(value.strip(), DATE_FORMAT)
    if end_of_day:
        return parsed.replace(hour=23, minute=59, second=59, microsecond=999000)
    return parsed


def record_timestamp(record: Dict) -> Optional[int]:
    """Return the millisecond timestamp of a record, if any."""
    for key in TIME_KEYS:
        value = record.get(key)
        if value:
            try:
                return int(value)
            except (TypeError, ValueError):
                continue
    return None


def is_comment(record: Dict) -> bool:
    return "comment_id" in record


def dedup(records: List[Dict]) -> List[Dict]:
    """Drop duplicated notes (by note_id) and comments (by comment_id)."""
    seen = set()
    result = []
    for record in records:
        key = record.get("comment_id") or "N:" + str(record.get("note_id") or id(record))
        if key in seen:
            continue
        seen.add(key)
        result.append(record)
    return result


def load_records(path: Path) -> List[Dict]:
    """Load a json array file or a jsonl file."""
    with open(path, "r", encoding="utf-8") as handle:
        raw = handle.read().strip()
    if not raw:
        return []
    if raw[0] == "[":
        data = json.loads(raw)
        return data if isinstance(data, list) else [data]
    return [json.loads(line) for line in raw.splitlines() if line.strip()]


def _scan_files(platform: str) -> List[Path]:
    """Collect json/jsonl data files of a platform, newest first."""
    root = DATA_DIR / platform
    if not root.exists():
        return []
    files = [
        path
        for path in root.rglob("*")
        if path.is_file()
        and path.suffix in (".json", ".jsonl")
        and not path.name.startswith(OUTPUT_PREFIX)
    ]
    return sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)


def _format_span(records: List[Dict]) -> str:
    stamps = sorted(ts for ts in (record_timestamp(r) for r in records) if ts)
    if not stamps:
        return ""
    start = datetime.fromtimestamp(stamps[0] / 1000).strftime(DATE_FORMAT)
    end = datetime.fromtimestamp(stamps[-1] / 1000).strftime(DATE_FORMAT)
    return f"{start} ~ {end}"


def filter_data_dir(platform: str, since: Optional[str] = None, until: Optional[str] = None) -> Dict:
    """Filter the newest data files of ``platform`` by publish time.

    Original files are left untouched; kept records are written to
    ``data/<platform>/filtered/filtered_notes_<stamp>.json`` (comments likewise).
    """
    if not since and not until:
        return {"skipped": True, "reason": "no time range configured"}

    low = parse_date(since) if since else None
    high = parse_date(until, end_of_day=True) if until else None
    if low and high and low > high:
        raise ValueError(f"起始日期 {since} 晚于结束日期 {until}")

    files = _scan_files(platform)
    records: List[Dict] = []
    scanned: List[Tuple[str, int]] = []
    for path in files:
        try:
            loaded = load_records(path)
        except Exception:
            continue
        if not loaded:
            continue
        records.extend(loaded)
        scanned.append((str(path.relative_to(PROJECT_ROOT)), len(loaded)))

    if not records:
        return {"scanned": scanned, "notes": (0, 0), "comments": (0, 0), "outputs": [], "notes_span": ""}

    records = dedup(records)
    notes = [r for r in records if not is_comment(r)]
    comments = [r for r in records if is_comment(r)]

    def keep(items: List[Dict]) -> List[Dict]:
        kept = []
        for record in items:
            stamp = record_timestamp(record)
            if stamp is None:
                continue
            moment = datetime.fromtimestamp(stamp / 1000)
            if low and moment < low:
                continue
            if high and moment > high:
                continue
            kept.append(record)
        return kept

    kept_notes = keep(notes)
    kept_comments = keep(comments)

    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    out_dir = DATA_DIR / platform / "filtered"
    outputs: List[str] = []

    for items, filename in (
        (kept_notes, f"{OUTPUT_PREFIX}notes_{stamp}.json"),
        (kept_comments, f"{OUTPUT_PREFIX}comments_{stamp}.json"),
    ):
        if not items:
            continue
        out_dir.mkdir(parents=True, exist_ok=True)
        target = out_dir / filename
        with open(target, "w", encoding="utf-8") as handle:
            json.dump(items, handle, ensure_ascii=False, indent=2)
        outputs.append(str(target.relative_to(PROJECT_ROOT)))

    return {
        "scanned": scanned,
        "window": (
            (since or "不限") + " ~ " + (until or "不限")
        ),
        "notes": (len(notes), len(kept_notes)),
        "comments": (len(comments), len(kept_comments)),
        "notes_span": _format_span(kept_notes),
        "outputs": outputs,
    }
