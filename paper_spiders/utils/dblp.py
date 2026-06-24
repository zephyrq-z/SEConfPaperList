"""
DBLP API utility for searching papers by title and extracting metadata.

Uses the DBLP API (https://dblp.org/faq/How+to+use+the+dblp+search+API.html)
Returns paper metadata including DOI, DBLP URL, and arXiv links.

Rate limit: DBLP is sensitive to burst requests. Use 3s+ delay between calls.
"""

import time
import re
import json
from urllib import parse as urlparse
from urllib import request as urlrequest
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)

DBLP_SEARCH_URL = "https://dblp.org/search/publ/api"
DBLP_DELAY = 3.0
DBLP_MAX_RETRIES = 2


def _clean_title_for_search(title: str) -> str:
    cleaned = re.sub(r'[^\w\s\-]', ' ', title)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned


def _extract_arxiv_id_from_doi(doi: str) -> str:
    match = re.search(r'ARXIV\.([\d]+\.[\d]+)', doi, re.IGNORECASE)
    return match.group(1) if match else ""


def search_dblp(title: str, conf: str = "", max_results: int = 5) -> Optional[Dict]:
    """Search DBLP API for a paper by its title.

    Returns:
        Dict with: doi, dblp_url, ee, arxiv_id, arxiv_url, venue, year
        or None if not found
    """
    cleaned_title = _clean_title_for_search(title)
    params = {"q": cleaned_title, "format": "json", "h": str(max_results)}
    url = f"{DBLP_SEARCH_URL}?{urlparse.urlencode(params)}"

    for attempt in range(DBLP_MAX_RETRIES):
        try:
            time.sleep(DBLP_DELAY)
            req = urlrequest.Request(url, headers={"User-Agent": "SEConfPaperList/1.0"})
            response = urlrequest.urlopen(req, timeout=15)
            data = json.loads(response.read().decode("utf-8"))

            hit_list = data.get("result", {}).get("hits", {}).get("hit", [])
            if not hit_list:
                return None

            conf_parts = conf.lower().split(" ") if conf else []
            conf_abbr = conf_parts[0] if conf_parts else ""
            conf_year = conf_parts[1] if len(conf_parts) > 1 else ""

            published = None
            arxiv_hit = None

            for hit in hit_list:
                info = hit.get("info", {})
                venue = info.get("venue", "").lower()
                doi = info.get("doi", "")
                is_arxiv = "corr" in venue or "arxiv" in doi.lower()
                is_published = not is_arxiv and venue != ""
                conf_match = (
                    conf_abbr in venue
                    or conf_abbr.upper() in info.get("venue", "")
                ) and str(info.get("year", "")) == conf_year

                if is_arxiv and arxiv_hit is None:
                    arxiv_hit = info
                elif is_published and (published is None or conf_match):
                    published = info

            result = {
                "doi": published.get("doi", "") if published else "",
                "dblp_url": published.get("url", "") if published else "",
                "ee": published.get("ee", "") if published else "",
                "arxiv_id": "",
                "arxiv_url": "",
                "venue": published.get("venue", "") if published else "",
                "year": str(published.get("year", "")) if published else "",
            }

            if arxiv_hit:
                arxiv_id = _extract_arxiv_id_from_doi(arxiv_hit.get("doi", ""))
                if arxiv_id:
                    result["arxiv_id"] = arxiv_id
                    result["arxiv_url"] = f"https://arxiv.org/abs/{arxiv_id}"

            if not result["doi"] and not result["arxiv_id"]:
                return None
            return result

        except Exception as e:
            if attempt < DBLP_MAX_RETRIES - 1:
                logger.warning(f"DBLP retry {attempt+1} for '{title[:50]}': {e}")
                time.sleep(5)
            else:
                logger.error(f"DBLP error for '{title[:50]}': {e}")
                return None

    return None


def get_full_version_url(dblp_data: Dict) -> str:
    """Get the best 'full version' URL. Priority: DOI > arXiv > DBLP page."""
    if dblp_data.get("doi"):
        return f"https://doi.org/{dblp_data['doi']}"
    if dblp_data.get("arxiv_url"):
        return dblp_data["arxiv_url"]
    if dblp_data.get("dblp_url"):
        return dblp_data["dblp_url"]
    return ""