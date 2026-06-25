#!/usr/bin/env python3
"""Test scraper: scrape up to 10 papers from a single conference URL.

The target URL is configured in TEST_CONF_URL inside this file.
Output: data/test_papers.jsonl
"""

import sys
import os
import logging
import requests
import orjson
from lxml import html as lxml_html

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from paper_spiders.utils.researchr import extract_form_params, fetch_detail_url, fetch_abstract, fetch_preprint_links

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ============================================================
# 配置：修改此处的 URL 和会议名称来测试不同会议
# ============================================================
TEST_CONF_URL = "https://conf.researchr.org/track/icse-2026/icse-2026-research-track"
TEST_CONF_NAME = "ICSE 2026"
TEST_LIMIT = 10  # 最多爬取多少篇
# ============================================================

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "data", "test_papers.jsonl")
HEADERS = {"User-Agent": "Mozilla/5.0"}


def scrape_listing(url, conf_name, limit):
    """Scrape paper titles and authors from a conference listing page."""
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    tree = lxml_html.fromstring(resp.content)

    table = tree.xpath('//*[@id="event-overview"]/table')
    if not table:
        logger.error(f"No event-overview table found for {conf_name}")
        return []

    papers = table[0].xpath("tr/td[2]")
    form_params = extract_form_params(resp.text)

    items = []
    for paper in papers:
        if len(items) >= limit:
            break

        title_el = paper.xpath("a[1]/text()")
        if not title_el:
            continue
        title = title_el[0].strip()

        author_els = paper.xpath('.//div[@class="performers"]/a/text()')
        author = ", ".join(a.strip() for a in author_els)

        uuid_el = paper.xpath("a[1]/@data-event-modal")
        uuid = uuid_el[0] if uuid_el else ""

        items.append({
            "conf": conf_name,
            "title": title,
            "author": author,
            "uuid": uuid,
            "form_params": form_params,
            "listing_url": url,
            "abstract": "",
            "full_version_url": "",
            "arxiv_url": "",
            "arxiv_pdf_url": "",
            "keywords": "",
            "title_cn": "",
            "abstract_cn": "",
            "arxiv_id": "",
            "doi": "",
            "dblp_url": "",
        })

    logger.info(f"Scraped {len(items)} papers from {conf_name}")
    return items


def enrich_papers(items):
    """Enrich papers with abstracts and arxiv links from researchr detail pages."""
    session = requests.Session()
    total = len(items)
    detail_ok = 0
    abstract_ok = 0
    preprint_ok = 0

    for idx, item in enumerate(items):
        uuid = item.get("uuid", "")
        form_params = item.get("form_params")
        listing_url = item.get("listing_url", "")

        if not uuid or not form_params:
            continue

        detail_url = fetch_detail_url(uuid, form_params, session, listing_url)
        if not detail_url:
            continue
        detail_ok += 1

        if not item.get("full_version_url"):
            item["full_version_url"] = detail_url

        if not item.get("abstract"):
            abstract = fetch_abstract(detail_url, session)
            if abstract:
                abstract_ok += 1
                item["abstract"] = abstract

        if not item.get("arxiv_pdf_url") or not item.get("arxiv_url"):
            links = fetch_preprint_links(detail_url, session)
            for link in links:
                if "arxiv.org/pdf/" in link and not item.get("arxiv_pdf_url"):
                    item["arxiv_pdf_url"] = link
                    item["arxiv_url"] = link.replace("/pdf/", "/abs/")
                    preprint_ok += 1
                elif "arxiv.org/abs/" in link and not item.get("arxiv_url"):
                    item["arxiv_url"] = link
                    item["arxiv_pdf_url"] = link.replace("/abs/", "/pdf/")
                    preprint_ok += 1

    logger.info(
        f"Enrich done: {total} papers, "
        f"detail={detail_ok}, abstract={abstract_ok}, preprint={preprint_ok}"
    )


def save_jsonl(items, path):
    """Save items to JSONL file atomically."""
    tmp = path + ".tmp"
    with open(tmp, "wb") as f:
        for item in items:
            out = {k: v for k, v in item.items()
                   if k not in ("form_params", "listing_url", "uuid")}
            for field in ["full_version_url", "arxiv_url", "arxiv_pdf_url", "abstract",
                          "keywords", "title_cn", "abstract_cn", "arxiv_id", "doi", "dblp_url"]:
                if field not in out:
                    out[field] = ""
            f.write(orjson.dumps(out) + b"\n")
    os.replace(tmp, path)
    logger.info(f"Saved {len(items)} papers to {path}")


def main():
    logger.info(f"Test scrape: {TEST_CONF_NAME} (limit={TEST_LIMIT})")

    items = scrape_listing(TEST_CONF_URL, TEST_CONF_NAME, TEST_LIMIT)
    if not items:
        logger.error("No papers scraped")
        sys.exit(1)

    logger.info("Enriching with researchr...")
    enrich_papers(items)

    abstract_ok = sum(1 for i in items if i.get("abstract"))
    arxiv_ok = sum(1 for i in items if i.get("arxiv_url"))
    logger.info(f"abstract={abstract_ok}, arxiv={arxiv_ok}")

    save_jsonl(items, OUTPUT_PATH)

    # Print summary
    print(f"\n{'='*60}")
    print(f"Results saved to: {OUTPUT_PATH}")
    print(f"{'='*60}")
    for i, item in enumerate(items):
        print(f"\n[{i+1}] {item['title']}")
        print(f"    Authors: {item['author']}")
        if item.get("abstract"):
            abstract_preview = item["abstract"][:120].replace("\n", " ")
            print(f"    Abstract: {abstract_preview}...")
        if item.get("arxiv_url"):
            print(f"    arXiv: {item['arxiv_url']}")


if __name__ == "__main__":
    main()