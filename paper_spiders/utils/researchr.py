"""
conf.researchr.org native scraping utility.

Extracts paper abstracts by:
1. POSTing to the modal AJAX endpoint to get the detail page URL
2. Fetching the detail page and extracting the abstract

No external API keys required.
"""

import re
import json
import time
import logging
from urllib import parse as urlparse
from urllib import request as urlrequest
from typing import Optional, Dict, List, Tuple
from scrapy.http import Response

logger = logging.getLogger(__name__)

AJAX_ENDPOINT = "https://conf.researchr.org/eventDetailsModalByAjaxConferenceEdition"


def extract_form_params(html: str) -> Optional[Dict]:
    """Extract the dynamic form parameters needed for modal AJAX requests."""
    idx = html.find("eventDetailsModalByAjaxConferenceEdition")
    if idx < 0:
        return None

    form_start = html.rfind("<form", 0, idx)
    form_end = html.find("</form>", idx)
    form_html = html[form_start : form_end + 7]

    button_match = re.search(r'serverInvoke\("[^"]+","([^"]+)"', form_html)
    name_match = re.search(r'name="([^"]+)"', form_html.split("action")[0])
    input_match = re.search(
        r'name="([^"]+)" type="text" value="" class="inputString form-control event-id-input"',
        form_html,
    )
    context_match = re.search(r'name="context" value="([^"]+)"', form_html)

    if not all([button_match, name_match, input_match, context_match]):
        return None

    return {
        "form_name": name_match.group(1),
        "input_field": input_match.group(1),
        "context": context_match.group(1),
        "action_name": button_match.group(1),
    }


def fetch_detail_url(
    uuid: str, form_params: Dict, session, listing_url: str
) -> Optional[str]:
    """Fetch the detail page URL for a paper via the modal AJAX endpoint."""
    data = {
        form_params["form_name"]: "1",
        "context": form_params["context"],
        form_params["input_field"]: uuid,
        form_params["action_name"]: "1",
        "__ajax_runtime_request__": "event-modal-loader",
    }

    try:
        resp = session.post(
            AJAX_ENDPOINT,
            data=data,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Referer": listing_url,
                "X-Requested-With": "XMLHttpRequest",
            },
            timeout=15,
        )
        result = json.loads(resp.text)
        modal_html = result[0]["value"]

        detail_match = re.search(r'href="([^"]*details[^"]*)"', modal_html)
        if detail_match:
            url = detail_match.group(1)
            if not url.startswith("http"):
                url = "https://conf.researchr.org" + url
            return url
    except Exception as e:
        logger.error(f"Modal error for UUID {uuid[:20]}: {e}")

    return None


def fetch_abstract(detail_url: str, session) -> str:
    """Fetch and extract the abstract from a detail page."""
    try:
        resp = session.get(
            detail_url,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=15,
        )
        html = resp.text

        match = re.search(
            r'Abstract</label><div class="col-sm-10">(.*?)</div>', html, re.DOTALL
        )
        if match:
            abstract = re.sub(r"<[^>]+>", "", match.group(1)).strip()
            return abstract
    except Exception as e:
        logger.error(f"Detail page error for {detail_url[:60]}: {e}")

    return ""


def fetch_preprint_links(detail_url: str, session) -> List[str]:
    """Extract pre-print (arXiv) links from the detail page."""
    try:
        resp = session.get(
            detail_url,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=15,
        )
        html = resp.text

        links = []
        for m in re.finditer(
            r'href="(https?://[^"]*arxiv[^"]*)"[^>]*>([^<]*)</a>', html
        ):
            links.append(m.group(1))
        return links
    except Exception:
        return []