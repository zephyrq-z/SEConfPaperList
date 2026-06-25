#!/usr/bin/env python3
"""Scrape papers from SE conferences and enrich with researchr metadata.

Usage:
    python scrape_papers.py              # scrape all conferences
    python scrape_papers.py --conf "ICSE 2026"  # scrape single conference

Output: paper_spiders/papers.jsonl
"""

import sys
import os
import time
import logging
import argparse

import requests
import orjson
from lxml import html as lxml_html

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from paper_spiders.utils.paperlist import paper_list
from paper_spiders.utils.researchr import extract_form_params, fetch_detail_url, fetch_abstract, fetch_preprint_links

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "paper_spiders", "papers.jsonl")
BATCH_SAVE_INTERVAL = 5  # save every N papers

HEADERS = {"User-Agent": "Mozilla/5.0"}


def scrape_listing(conf_info):
    """Scrape paper titles, authors, and UUIDs from a conference listing page."""
    url = conf_info["url"]
    conf = conf_info["conf"]

    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    tree = lxml_html.fromstring(resp.content)

    # Parse the event-overview table
    table = tree.xpath('//*[@id="event-overview"]/table')
    if not table:
        logger.warning(f"No event-overview table found for {conf}")
        return []

    papers = table[0].xpath("tr/td[2]")
    form_params = extract_form_params(resp.text)

    items = []
    for paper in papers:
        title_el = paper.xpath("a[1]/text()")
        if not title_el:
            continue
        title = title_el[0].strip()

        author_els = paper.xpath('.//div[@class="performers"]/a/text()')
        author = ", ".join(a.strip() for a in author_els)

        uuid_el = paper.xpath("a[1]/@data-event-modal")
        uuid = uuid_el[0] if uuid_el else ""

        items.append({
            "conf": conf,
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

        if (idx + 1) % 50 == 0:
            logger.info(
                f"Enrich: {idx + 1}/{total} "
                f"(detail={detail_ok}, abstract={abstract_ok}, preprint={preprint_ok})"
            )

    logger.info(
        f"Enrich done: {total} papers, "
        f"detail={detail_ok}, abstract={abstract_ok}, preprint={preprint_ok}"
    )


def deduplicate_and_sort(items):
    """Remove duplicates and sort by year (desc), venue, title."""
    seen = set()
    unique = []
    for item in items:
        title = item["title"].replace("[Remote] ", "")
        item["title"] = title
        if title in seen:
            continue
        seen.add(title)
        if not item["conf"] or not title or not item["author"] or title.startswith("Q&A ("):
            continue
        unique.append(item)

    venue_order = {"ICSE": 0, "FSE": 1, "ASE": 2, "ISSTA": 3}
    unique.sort(key=lambda x: (
        -int(x["conf"].split(" ")[-1]),
        venue_order.get(x["conf"].split(" ")[0], 99),
        x["title"],
    ))
    return unique


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
    parser = argparse.ArgumentParser(description="Scrape SE conference papers")
    parser.add_argument("--conf", help="Scrape a single conference (e.g. 'ICSE 2026')")
    args = parser.parse_args()

    start = time.time()

    targets = paper_list
    if args.conf:
        targets = [p for p in paper_list if p["conf"] == args.conf]
        if not targets:
            logger.error(f"Conference '{args.conf}' not found in paper_list")
            sys.exit(1)

    all_items = []
    for conf_info in targets:
        logger.info(f"Scraping {conf_info['conf']}...")
        items = scrape_listing(conf_info)
        logger.info(f"  {conf_info['conf']}: {len(items)} papers")
        all_items.extend(items)

    logger.info(f"Total scraped: {len(all_items)} papers")

    logger.info("Enriching with researchr...")
    enrich_papers(all_items)

    abstract_ok = sum(1 for i in all_items if i.get("abstract"))
    arxiv_ok = sum(1 for i in all_items if i.get("arxiv_url"))
    logger.info(f"abstract={abstract_ok}, arxiv={arxiv_ok}")

    all_items = deduplicate_and_sort(all_items)
    logger.info(f"After dedup/sort: {len(all_items)} papers")

    save_jsonl(all_items, OUTPUT_PATH)

    elapsed = time.time() - start
    logger.info(f"Done in {elapsed/60:.1f} minutes")


if __name__ == "__main__":
    main()