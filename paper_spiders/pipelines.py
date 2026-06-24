# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html
import scrapy
from typing import Dict, List
from .utils.paperlist import paper_list
import os
import orjson
import logging
import requests as req

logger = logging.getLogger(__name__)


def jsonline2md(jsonline: list[dict], header: List[str]) -> str:
    md = ""
    for h in header:
        md += f"| {h} "
    md += "|\n"
    for h in header:
        md += "| --- "
    md += "|\n"
    for j in jsonline:
        for h in header:
            val = j.get(h, "")
            val = str(val).replace("|", "\\|").replace("\n", " ")
            md += f"| {val} "
        md += "|\n"
    return md


class PaperToMarkdownPipeline:
    def __init__(self):
        self.content = []
        self.jsonl_path = "./paper_spiders/papers.jsonl"
        self.md_path = "./paper_spiders/papers.md"
        self.enrich = os.environ.get("ENRICH", "1") == "1"
        self.enrich_source = os.environ.get("ENRICH_SOURCE", "researchr")
        self.enrich_translate = os.environ.get("ENRICH_TRANSLATE", "0") == "1"
        self.translate_api_key = os.environ.get("OPENAI_API_KEY", "")
        self.translate_base_url = os.environ.get("OPENAI_BASE_URL", "")
        self.translate_model = os.environ.get("TRANSLATE_MODEL", "")

    def _update_and_sort(self):
        if os.path.exists(self.jsonl_path):
            with open(self.jsonl_path, "r") as f:
                old_content = f.readlines()
            old_content = [orjson.loads(x) for x in old_content]
            self.content = self.content + old_content

        _content = []
        title_set = set()
        for item in self.content:
            item["title"] = item["title"].replace("[Remote] ", "")
            if item["title"] in title_set:
                continue
            title_set.add(item["title"])
            if (
                item["conf"] == ""
                or item["title"] == ""
                or item["author"] == ""
                or item["title"].startswith("Q&A (")
            ):
                continue
            _content.append(item)

        self.content = sorted(
            _content,
            key=lambda x: (
                -1 * int(x["conf"].split(" ")[-1]),
                ["ICSE", "FSE", "ASE", "ISSTA"].index(x["conf"].split(" ")[0]),
                x["title"],
            ),
        )

    def _enrich_with_researchr(self):
        """Enrich papers by scraping conf.researchr.org detail pages."""
        from .utils.researchr import fetch_detail_url, fetch_abstract, fetch_preprint_links

        total = len(self.content)
        detail_ok = 0
        abstract_ok = 0
        preprint_ok = 0

        # Create a session for all requests
        session = req.Session()

        for idx, item in enumerate(self.content):
            uuid = item.get("uuid", "")
            form_params = item.get("form_params")
            listing_url = item.get("listing_url", "")

            if not uuid or not form_params:
                continue

            # Step 1: Get detail URL from modal
            detail_url = fetch_detail_url(uuid, form_params, session, listing_url)
            if not detail_url:
                continue
            detail_ok += 1

            # Set full_version_url to the detail page
            if not item.get("full_version_url"):
                item["full_version_url"] = detail_url

            # Step 2: Fetch abstract from detail page
            if not item.get("abstract"):
                abstract = fetch_abstract(detail_url, session)
                if abstract:
                    abstract_ok += 1
                    item["abstract"] = abstract

            # Step 3: Fetch pre-print links from detail page
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

            # Set defaults
            for field in [
                "full_version_url", "arxiv_url", "arxiv_pdf_url",
                "abstract", "keywords", "doi", "dblp_url", "arxiv_id",
            ]:
                if field not in item or not item[field]:
                    item[field] = ""

            if (idx + 1) % 50 == 0:
                logger.info(
                    f"Researchr: {idx + 1}/{total} "
                    f"(detail={detail_ok}, abstract={abstract_ok}, preprint={preprint_ok})"
                )

        logger.info(
            f"Researchr done: {total} papers, "
            f"detail={detail_ok}, abstract={abstract_ok}, preprint={preprint_ok}"
        )

    def _enrich_with_external(self):
        """Enrich papers using external APIs (DBLP + arXiv + Semantic Scholar)."""
        from .utils.dblp import search_dblp, get_full_version_url
        from .utils.arxiv import fetch_arxiv_by_id
        from .utils.semantic_scholar import fetch_by_doi

        total = len(self.content)
        dblp_hits = 0
        arxiv_hits = 0
        s2_hits = 0

        for idx, item in enumerate(self.content):
            title = item.get("title", "")
            conf = item.get("conf", "")

            dblp_data = search_dblp(title, conf)
            if dblp_data:
                dblp_hits += 1

                if not item.get("full_version_url"):
                    item["full_version_url"] = get_full_version_url(dblp_data)
                if not item.get("doi"):
                    item["doi"] = dblp_data.get("doi", "")
                if not item.get("dblp_url"):
                    item["dblp_url"] = dblp_data.get("dblp_url", "")

                arxiv_id = dblp_data.get("arxiv_id", "")
                if arxiv_id:
                    item["arxiv_id"] = arxiv_id
                    item["arxiv_url"] = item.get("arxiv_url") or f"https://arxiv.org/abs/{arxiv_id}"
                    item["arxiv_pdf_url"] = item.get("arxiv_pdf_url") or f"https://arxiv.org/pdf/{arxiv_id}"

                    if not item.get("abstract"):
                        arxiv_data = fetch_arxiv_by_id(arxiv_id)
                        if arxiv_data:
                            arxiv_hits += 1
                            item["abstract"] = arxiv_data.get("abstract", "")
                            item["keywords"] = ", ".join(arxiv_data.get("keywords", []))

                if not item.get("abstract") and item.get("doi"):
                    s2_data = fetch_by_doi(item["doi"])
                    if s2_data:
                        s2_hits += 1
                        item["abstract"] = s2_data.get("abstract", "")

            for field in [
                "full_version_url", "arxiv_url", "arxiv_pdf_url",
                "abstract", "keywords", "doi", "dblp_url", "arxiv_id",
            ]:
                if field not in item or not item[field]:
                    item[field] = ""

            if (idx + 1) % 50 == 0:
                logger.info(
                    f"External: {idx + 1}/{total} "
                    f"(DBLP={dblp_hits}, arXiv={arxiv_hits}, S2={s2_hits})"
                )

        logger.info(
            f"External done: {total} papers, "
            f"DBLP={dblp_hits}, arXiv={arxiv_hits}, S2={s2_hits}"
        )

    def _enrich_with_translation(self):
        if not self.translate_api_key:
            logger.warning("No OPENAI_API_KEY set, skipping translation")
            return

        from .utils.translate import translate_batch

        items_to_translate = []
        for item in self.content:
            if not item.get("title_cn") or not item.get("abstract_cn"):
                items_to_translate.append(item)

        if items_to_translate:
            logger.info(f"Translating {len(items_to_translate)} papers...")
            translate_batch(
                items_to_translate,
                self.translate_api_key,
                self.translate_base_url,
                self.translate_model,
            )

        for item in self.content:
            if not item.get("title_cn"):
                item["title_cn"] = ""
            if not item.get("abstract_cn"):
                item["abstract_cn"] = ""

    def process_item(self, item: Dict, spider):
        normalized = {
            "conf": item.get("conf", ""),
            "title": item.get("title", ""),
            "author": item.get("author", ""),
            "abstract": item.get("abstract", ""),
            "full_version_url": item.get("full_version_url", ""),
            "arxiv_url": item.get("arxiv_url", ""),
            "arxiv_pdf_url": item.get("arxiv_pdf_url", ""),
            "keywords": item.get("keywords", ""),
            "title_cn": item.get("title_cn", ""),
            "abstract_cn": item.get("abstract_cn", ""),
            "arxiv_id": item.get("arxiv_id", ""),
            "doi": item.get("doi", ""),
            "dblp_url": item.get("dblp_url", ""),
            "uuid": item.get("uuid", ""),
            "form_params": item.get("form_params"),
            "listing_url": item.get("listing_url", ""),
        }
        self.content.append(normalized)
        return item

    def open_spider(self, spider: scrapy.Spider):
        spider.log("spider open")

    def close_spider(self, spider):
        spider.log("spider close")

        self._update_and_sort()

        if self.enrich:
            if self.enrich_source == "researchr":
                logger.info("Using researchr native scraping for enrichment")
                self._enrich_with_researchr()
            elif self.enrich_source == "external":
                logger.info("Using external APIs (DBLP/arXiv/S2) for enrichment")
                self._enrich_with_external()
            else:
                logger.warning(f"Unknown ENRICH_SOURCE={self.enrich_source}, skipping enrichment")

        if self.enrich_translate:
            self._enrich_with_translation()

        # Write JSONL
        with open(self.jsonl_path, "w") as f:
            for c in self.content:
                # Remove internal fields before writing
                output = {k: v for k, v in c.items() if k not in ("form_params", "listing_url", "uuid")}
                f.write(orjson.dumps(output).decode("utf-8") + "\n")

        # Write Markdown
        headers = [
            "conf", "title", "author", "abstract", "keywords",
            "full_version_url", "arxiv_url", "arxiv_pdf_url",
            "title_cn", "abstract_cn",
        ]
        md = jsonline2md(self.content, headers)
        with open(self.md_path, "w") as f:
            f.write(md)

        # Update README
        with open("README.md", "r+") as f:
            readme = f.read()
            start_idx = readme.find("### Papers\n")
            end_idx = readme.find("\n### Acknowledgments\n")
            readme_headers = ["conf", "title", "author"]
            readme_md = jsonline2md(self.content, readme_headers)
            readme_md = (
                readme_md.replace("conf", "Conference")
                .replace("title", "Title")
                .replace("author", "Authors")
            )
            if start_idx >= 0 and end_idx >= 0:
                readme = readme[: start_idx + 11] + readme_md + readme[end_idx:]
                f.seek(0)
                f.write(readme)
                f.truncate()