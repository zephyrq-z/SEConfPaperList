#!/usr/bin/env python3
"""Translate paper titles and abstracts to Chinese with resume support.

Usage:
    python translate_papers.py                           # translate all untranslated papers
    python translate_papers.py --force                   # re-translate all papers
    python translate_papers.py --dry-run                 # show how many papers need translation
    python translate_papers.py --input data/run2.jsonl   # translate custom input file

Saves progress after each batch. If interrupted, simply re-run to resume.
"""

import argparse
import logging
import os
import sys
import time

from dotenv import load_dotenv

_ENV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(_ENV_PATH, override=True)

from lib.io import load_jsonl, save_jsonl
from lib.translate import translate_batch

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_INPUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "papers.jsonl")
BATCH_SIZE = 10


def is_translated(item: dict) -> bool:
    tc = item.get("title_cn", "")
    ac = item.get("abstract_cn", "")
    return bool(tc) and bool(ac)


def main() -> None:
    parser = argparse.ArgumentParser(description="Translate paper titles and abstracts to Chinese")
    parser.add_argument("--input", default=DEFAULT_INPUT,
                        help=f"Input JSONL file (default: {DEFAULT_INPUT})")
    parser.add_argument("--force", action="store_true",
                        help="Re-translate all papers, ignoring existing translations")
    parser.add_argument("--dry-run", action="store_true",
                        help="Only show how many papers need translation")
    args = parser.parse_args()

    input_path = args.input
    logger.info("Loading papers from %s", input_path)
    all_papers = load_jsonl(input_path)
    logger.info("Loaded %d papers", len(all_papers))

    if args.force:
        to_translate = all_papers
        for p in all_papers:
            p["title_cn"] = ""
            p["abstract_cn"] = ""
    else:
        to_translate = [p for p in all_papers if not is_translated(p)]

    done_count = len(all_papers) - len(to_translate)
    logger.info("Already translated: %d", done_count)
    logger.info("Need translation: %d", len(to_translate))

    if args.dry_run:
        if to_translate:
            logger.info("Papers to translate:")
            for p in to_translate[:10]:
                logger.info("  [%s] %s", p["conf"], p["title"][:80])
            if len(to_translate) > 10:
                logger.info("  ... and %d more", len(to_translate) - 10)
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
    logger.info("API: %s (model: %s)", base_url[:60], model)
    translated = 0
    total = len(to_translate)
    total_batches = (total + BATCH_SIZE - 1) // BATCH_SIZE
    print(f"Translating {total} papers in {total_batches} batches...")

    for i in range(0, total, BATCH_SIZE):
        batch = to_translate[i:i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1

        translate_batch(batch, api_key, base_url, model)

        ok = sum(1 for p in batch if is_translated(p))
        translated += ok
        pct = translated * 100 // total
        bar_width = 30
        filled = pct * bar_width // 100
        bar = "\u2588" * filled + "\u2591" * (bar_width - filled)
        elapsed = time.time() - start
        rate = translated / elapsed if elapsed > 0 else 0
        eta = (total - translated) / rate if rate > 0 else 0
        print(f"\r  [{bar}] {pct:3d}%  {translated}/{total}  {rate:.1f}p/s  ETA {eta/60:.0f}m  ", end="", flush=True)

        save_jsonl(all_papers, input_path)

    print()
    elapsed = time.time() - start
    logger.info("Done: %d papers translated in %.1f minutes", translated, elapsed / 60)


if __name__ == "__main__":
    main()