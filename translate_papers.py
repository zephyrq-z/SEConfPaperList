#!/usr/bin/env python3
"""Translate paper titles and abstracts to Chinese with resume support.

Usage:
    python translate_papers.py              # translate all untranslated papers
    python translate_papers.py --force      # re-translate all papers (ignore existing)
    python translate_papers.py --dry-run    # show how many papers need translation

The script saves progress after each batch. If interrupted, simply re-run it
to resume from where it left off.

Requires: OPENAI_API_KEY (and optionally OPENAI_BASE_URL, TRANSLATE_MODEL)
"""

import sys
import os
import time
import logging
import argparse

import orjson

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
_ENV_PATH = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(_ENV_PATH)

from paper_spiders.utils.translate import translate_batch

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

INPUT_PATH = os.path.join(os.path.dirname(__file__), "data", "papers.jsonl")
BATCH_SIZE = 10


def load_papers(path):
    """Load papers from JSONL file."""
    if not os.path.exists(path):
        logger.error(f"File not found: {path}")
        logger.error("Run 'python scrape_papers.py' first.")
        sys.exit(1)

    with open(path, "rb") as f:
        return [orjson.loads(line) for line in f if line.strip()]


def save_papers(papers, path):
    """Save papers to JSONL file atomically."""
    tmp = path + ".tmp"
    with open(tmp, "wb") as f:
        for item in papers:
            f.write(orjson.dumps(item) + b"\n")
    os.replace(tmp, path)


def is_translated(item):
    """Check if a paper has both title and abstract translated."""
    return bool(item.get("title_cn", "").strip()) and bool(item.get("abstract_cn", "").strip())


def main():
    parser = argparse.ArgumentParser(description="Translate paper titles and abstracts to Chinese")
    parser.add_argument("--force", action="store_true",
                        help="Re-translate all papers, ignoring existing translations")
    parser.add_argument("--dry-run", action="store_true",
                        help="Only show how many papers need translation, don't translate")
    args = parser.parse_args()

    logger.info(f"Loading papers from {INPUT_PATH}")
    all_papers = load_papers(INPUT_PATH)
    logger.info(f"Loaded {len(all_papers)} papers")

    if args.force:
        to_translate = all_papers
        for p in all_papers:
            p["title_cn"] = ""
            p["abstract_cn"] = ""
    else:
        to_translate = [p for p in all_papers if not is_translated(p)]

    done_count = len(all_papers) - len(to_translate)
    logger.info(f"Already translated: {done_count}")
    logger.info(f"Need translation: {len(to_translate)}")

    if args.dry_run:
        if to_translate:
            logger.info("Papers to translate:")
            for p in to_translate[:10]:
                logger.info(f"  [{p['conf']}] {p['title'][:80]}")
            if len(to_translate) > 10:
                logger.info(f"  ... and {len(to_translate) - 10} more")
        return

    if not to_translate:
        logger.info("All papers already translated. Use --force to re-translate.")
        return

    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        logger.error("OPENAI_API_KEY not set. Set it in .env or export it.")
        sys.exit(1)

    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
    model = os.environ.get("TRANSLATE_MODEL", "gpt-4o-mini")

    start = time.time()
    translated = 0

    for i in range(0, len(to_translate), BATCH_SIZE):
        batch = to_translate[i:i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        total_batches = (len(to_translate) + BATCH_SIZE - 1) // BATCH_SIZE

        logger.info(f"Batch {batch_num}/{total_batches} ({len(batch)} papers)...")

        translate_batch(batch, api_key, base_url, model)

        # Count successful translations in this batch
        ok = sum(1 for p in batch if is_translated(p))
        translated += ok

        # Save progress after each batch
        save_papers(all_papers, INPUT_PATH)
        logger.info(f"  {ok}/{len(batch)} translated, saved (total progress: {done_count + translated}/{len(all_papers)})")

    elapsed = time.time() - start
    logger.info(f"Done: {translated} papers translated in {elapsed/60:.1f} minutes")


if __name__ == "__main__":
    main()