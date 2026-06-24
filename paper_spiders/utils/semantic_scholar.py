"""
Semantic Scholar API utility for fetching paper abstracts by DOI.

Free API: 1 req/s anonymous, 100 req/s with API key.
Set SEMANTIC_SCHOLAR_API_KEY env var for higher rate limits.
"""

import time
import json
from urllib import request as urlrequest
from urllib.parse import quote
from typing import Optional
import logging
import os

logger = logging.getLogger(__name__)

API_URL = "https://api.semanticscholar.org/graph/v1"
API_KEY = os.environ.get("SEMANTIC_SCHOLAR_API_KEY", "")
DELAY = 1.0 if API_KEY else 3.0  # 100/s with key, ~1/s without


def fetch_by_doi(doi: str) -> Optional[dict]:
    """Fetch paper metadata from Semantic Scholar by DOI.

    Returns:
        Dict with: abstract, title, url, or None if not found
    """
    if not doi:
        return None

    url = f"{API_URL}/paper/DOI:{quote(doi)}?fields=title,abstract,url"

    try:
        time.sleep(DELAY)
        req = urlrequest.Request(url)
        if API_KEY:
            req.add_header("x-api-key", API_KEY)
        response = urlrequest.urlopen(req, timeout=15)
        data = json.loads(response.read().decode("utf-8"))

        if not data or not data.get("abstract"):
            return None

        logger.info(f"S2 abstract for DOI {doi[:30]}... ({len(data['abstract'])} chars)")
        return {
            "abstract": data.get("abstract", ""),
            "title": data.get("title", ""),
            "url": data.get("url", ""),
        }

    except Exception as e:
        logger.error(f"S2 error for DOI '{doi[:30]}': {e}")
        return None