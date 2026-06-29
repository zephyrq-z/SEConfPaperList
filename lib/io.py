"""JSONL I/O helpers shared across all scripts."""

import json
import os
import logging

logger = logging.getLogger(__name__)


def load_jsonl(path: str) -> list[dict]:
    """Load all papers from a JSONL file."""
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def save_jsonl(items: list[dict], path: str) -> None:
    """Atomically save papers to a JSONL file."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    os.replace(tmp, path)
    logger.info(f"Saved {len(items)} papers to {path}")


def load_existing(path: str) -> dict[tuple[str, str], dict]:
    """Load existing papers keyed by (conf, title) for dedup."""
    existing = {}
    for p in load_jsonl(path):
        key = (p.get("conf", ""), p.get("title", ""))
        existing[key] = p
    return existing


def merge_items(existing: dict, new_items: list[dict]) -> list[dict]:
    """Merge new items into existing, replacing duplicates by (conf, title)."""
    merged = dict(existing)
    for item in new_items:
        key = (item.get("conf", ""), item.get("title", ""))
        merged[key] = item
    return list(merged.values())