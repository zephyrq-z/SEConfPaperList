"""
arXiv API utility for fetching paper metadata by arXiv ID.

Uses the arXiv API (https://info.arxiv.org/help/api/index.html)
"""

import time
import re
import xml.etree.ElementTree as ET
from urllib import request as urlrequest
from urllib import parse as urlparse
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)

ARXIV_API_URL = "https://export.arxiv.org/api/query"
ATOM_NAMESPACE = "{http://www.w3.org/2005/Atom}"
ARXIV_NAMESPACE = "{http://arxiv.org/schemas/atom}"


def fetch_arxiv_by_id(arxiv_id: str) -> Optional[Dict]:
    """Fetch arXiv metadata by arXiv paper ID.

    Args:
        arxiv_id: arXiv paper ID, e.g., "2401.08807"

    Returns:
        Dict with keys: abstract, arxiv_url, arxiv_pdf_url, keywords
        or None if not found
    """
    # Clean the ID (remove version suffix if present)
    arxiv_id = re.sub(r'v\d+$', '', arxiv_id.strip())

    params = {
        "id_list": arxiv_id,
        "max_results": "1",
    }
    query_string = urlparse.urlencode(params)
    url = f"{ARXIV_API_URL}?{query_string}"

    try:
        time.sleep(0.5)
        response = urlrequest.urlopen(url, timeout=15)
        content = response.read().decode("utf-8")

        root = ET.fromstring(content)
        entries = root.findall(f"{ATOM_NAMESPACE}entry")

        if not entries:
            logger.info(f"No arXiv entry for ID: {arxiv_id}")
            return None

        entry = entries[0]

        # Extract abstract
        abstract_elem = entry.find(f"{ATOM_NAMESPACE}summary")
        abstract = (
            abstract_elem.text.strip()
            if abstract_elem is not None and abstract_elem.text
            else ""
        )

        # Extract URLs
        arxiv_url = ""
        arxiv_pdf_url = ""
        for link in entry.findall(f"{ATOM_NAMESPACE}link"):
            rel = link.get("rel", "")
            href = link.get("href", "")
            title_attr = link.get("title", "")

            if rel == "alternate":
                arxiv_url = href
            elif "pdf" in title_attr.lower():
                arxiv_pdf_url = href

        if not arxiv_url:
            arxiv_url = f"https://arxiv.org/abs/{arxiv_id}"
        if not arxiv_pdf_url:
            arxiv_pdf_url = f"https://arxiv.org/pdf/{arxiv_id}"

        # Extract categories
        categories = []
        for cat in entry.findall(f"{ATOM_NAMESPACE}category"):
            term = cat.get("term", "")
            if term:
                categories.append(term)

        primary_cat = entry.find(f"{ARXIV_NAMESPACE}primary_category")
        if primary_cat is not None:
            primary_term = primary_cat.get("term", "")
            if primary_term and primary_term not in categories:
                categories.insert(0, primary_term)

        logger.info(f"Fetched arXiv data for: {arxiv_id}")
        return {
            "abstract": abstract,
            "arxiv_url": arxiv_url,
            "arxiv_pdf_url": arxiv_pdf_url,
            "keywords": categories,
        }

    except Exception as e:
        logger.error(f"arXiv API error for ID '{arxiv_id}': {e}")
        return None