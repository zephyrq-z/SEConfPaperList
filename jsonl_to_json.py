#!/usr/bin/env python3
"""Convert papers.jsonl to structured papers.json grouped by conference.

Usage:
    python jsonl_to_json.py

The output format groups papers by conference, making it easy to manually
add, remove, or edit papers:

    {
      "ICSE 2026": [
        {
          "title": "...",
          "authors": "...",
          "abstract": "...",
          ...
        }
      ],
      "FSE 2026": [...]
    }
"""

import sys
import os
import json
from collections import OrderedDict

import orjson

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from paper_spiders.utils.paperlist import paper_list

JSONL_PATH = os.path.join(os.path.dirname(__file__), "paper_spiders", "papers.jsonl")
JSON_PATH = os.path.join(os.path.dirname(__file__), "paper_spiders", "papers.json")

FIELDS = [
    "title", "authors", "abstract", "full_version_url",
    "arxiv_url", "arxiv_pdf_url", "title_cn", "abstract_cn",
]


def convert():
    if not os.path.exists(JSONL_PATH):
        print(f"Error: {JSONL_PATH} not found. Run scrape_papers.py first.")
        sys.exit(1)

    with open(JSONL_PATH, "rb") as f:
        papers = [orjson.loads(line) for line in f if line.strip()]

    # Preserve conference order from paper_list
    result = OrderedDict()
    for conf_info in paper_list:
        result[conf_info["conf"]] = []

    for p in papers:
        conf = p.get("conf", "")
        if conf not in result:
            result[conf] = []
        result[conf].append({
            "title": p.get("title", ""),
            "authors": p.get("author", ""),
            "abstract": p.get("abstract", ""),
            "full_version_url": p.get("full_version_url", ""),
            "arxiv_url": p.get("arxiv_url", ""),
            "arxiv_pdf_url": p.get("arxiv_pdf_url", ""),
            "title_cn": p.get("title_cn", ""),
            "abstract_cn": p.get("abstract_cn", ""),
        })

    # Remove empty conferences
    result = OrderedDict((k, v) for k, v in result.items() if v)

    # Write atomically
    tmp = JSON_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    os.replace(tmp, JSON_PATH)

    total = sum(len(v) for v in result.values())
    for conf, papers_list in result.items():
        print(f"  {conf}: {len(papers_list)} papers")
    print(f"Total: {total} papers → {JSON_PATH}")


if __name__ == "__main__":
    convert()