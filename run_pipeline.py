#!/usr/bin/env python3
"""Run the full pipeline: scrape papers then translate them.

This is a convenience wrapper that calls the two independent scripts sequentially.
For more control, run them separately:

    python scrape_papers.py              # scrape and enrich papers
    python translate_papers.py           # translate titles and abstracts
"""

import subprocess
import sys
import os

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))


def run(script_name):
    path = os.path.join(SCRIPTS_DIR, script_name)
    print(f"\n{'=' * 60}")
    print(f"Running: {script_name}")
    print(f"{'=' * 60}\n")
    result = subprocess.run([sys.executable, path], cwd=SCRIPTS_DIR)
    if result.returncode != 0:
        print(f"\n{script_name} failed with exit code {result.returncode}", file=sys.stderr)
        sys.exit(result.returncode)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run full scrape + translate pipeline")
    parser.add_argument("--scrape-only", action="store_true", help="Only scrape, skip translation")
    parser.add_argument("--translate-only", action="store_true", help="Only translate, skip scraping")
    parser.add_argument("--conf", help="Scrape a single conference (e.g. 'ICSE 2026')")
    args = parser.parse_args()

    if args.translate_only:
        run("translate_papers.py")
    elif args.scrape_only:
        cmd = [sys.executable, "scrape_papers.py"]
        if args.conf:
            cmd.extend(["--conf", args.conf])
        subprocess.run(cmd, cwd=SCRIPTS_DIR)
    else:
        cmd = [sys.executable, "scrape_papers.py"]
        if args.conf:
            cmd.extend(["--conf", args.conf])
        result = subprocess.run(cmd, cwd=SCRIPTS_DIR)
        if result.returncode != 0:
            sys.exit(result.returncode)
        run("translate_papers.py")