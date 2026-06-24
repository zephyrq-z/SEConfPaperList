#!/usr/bin/env python3
"""Run full pipeline: scrape all conferences + enrich with researchr."""
import sys, os, logging, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
logging.basicConfig(level=logging.WARNING, stream=sys.stderr)

import requests
from scrapy.http import HtmlResponse
from paper_spiders.spiders.paper_spider import PaperSpider
from paper_spiders.utils.paperlist import paper_list
from paper_spiders.pipelines import PaperToMarkdownPipeline, jsonline2md
import orjson

start = time.time()

# Scrape
all_items = []
for conf_info in paper_list:
    url = conf_info["url"]
    conf = conf_info["conf"]
    resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
    response = HtmlResponse(url=url, body=resp.content, encoding='utf-8')
    items = list(PaperSpider().parse(response, conf=conf, url=url))
    all_items.extend(items)
    sys.stderr.write(f"Scraped {conf}: {len(items)} papers\n")
    sys.stderr.flush()

sys.stderr.write(f"Total: {len(all_items)} papers\n")
sys.stderr.flush()

# Enrich
sys.stderr.write("Enriching with researchr...\n")
sys.stderr.flush()
pipeline = PaperToMarkdownPipeline()
pipeline.enrich = True
pipeline.enrich_source = "researchr"
pipeline.enrich_translate = False
pipeline.content = all_items
pipeline._enrich_with_researchr()

abstract_ok = sum(1 for i in pipeline.content if i.get("abstract"))
detail_ok = sum(1 for i in pipeline.content if i.get("full_version_url"))
arxiv_ok = sum(1 for i in pipeline.content if i.get("arxiv_url"))
sys.stderr.write(f"abstract={abstract_ok}, detail_url={detail_ok}, arxiv={arxiv_ok}\n")
sys.stderr.flush()

# Sort and write
pipeline._update_and_sort()
sys.stderr.write(f"After sort: {len(pipeline.content)}\n")

with open("./paper_spiders/papers.jsonl", "w") as f:
    for item in pipeline.content:
        out = {k: v for k, v in item.items() if k not in ("form_params", "listing_url", "uuid")}
        for field in ["full_version_url", "arxiv_url", "arxiv_pdf_url", "abstract",
                       "keywords", "title_cn", "abstract_cn", "arxiv_id", "doi", "dblp_url"]:
            if field not in out: out[field] = ""
        f.write(orjson.dumps(out).decode("utf-8") + "\n")

headers = ["conf", "title", "author", "abstract", "keywords",
           "full_version_url", "arxiv_url", "arxiv_pdf_url", "title_cn", "abstract_cn"]
with open("./paper_spiders/papers.md", "w") as f:
    f.write(jsonline2md(pipeline.content, headers))

with open("README.md", "r+") as f:
    readme = f.read()
    si = readme.find("### Papers\n")
    ei = readme.find("\n### Acknowledgments\n")
    rm = jsonline2md(pipeline.content, ["conf", "title", "author"])
    rm = rm.replace("conf", "Conference").replace("title", "Title").replace("author", "Authors")
    if si >= 0 and ei >= 0:
        readme = readme[:si+11] + rm + readme[ei:]
        f.seek(0); f.write(readme); f.truncate()

elapsed = time.time() - start
sys.stderr.write(f"Done in {elapsed/60:.0f} minutes\n")
sys.stderr.flush()