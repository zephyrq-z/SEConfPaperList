"""conf.researchr.org scraping — extract abstracts and arXiv links."""

import re
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

AJAX_ENDPOINT = "https://conf.researchr.org/eventDetailsModalByAjaxConferenceEdition"


def extract_form_params(html: str) -> Optional[dict]:
    """Extract dynamic form parameters for modal AJAX (per-page hashes)."""
    idx = html.find("eventDetailsModalByAjaxConferenceEdition")
    if idx < 0:
        return None

    form_start = html.rfind("<form", 0, idx)
    form_end = html.find("</form>", idx)
    if form_start < 0 or form_end < 0:
        return None
    form_html = html[form_start: form_end + 7]

    # First hidden input name = form_name
    name_match = re.search(r'name="([^"]+)"', form_html.split("action")[0])
    # UUID input: class contains "event-id"
    input_match = re.search(r'name="([^"]+)"[^>]*class="[^"]*event-id[^"]*"', form_html)
    # serverInvoke action
    button_match = re.search(r'serverInvoke\("[^"]+","([^"]+)"', form_html)
    # context value
    context_match = re.search(r'name="context" value="([^"]+)"', form_html)

    if not all([name_match, input_match, button_match, context_match]):
        return None

    return {
        "form_name": name_match.group(1),
        "input_field": input_match.group(1),
        "context": context_match.group(1),
        "action_name": button_match.group(1),
    }


def fetch_detail_url(uuid: str, form_params: dict, session, listing_url: str) -> Optional[str]:
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
            AJAX_ENDPOINT, data=data,
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
        resp = session.get(detail_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        match = re.search(
            r'Abstract</label><div class="col-sm-10">(.*?)</div>', resp.text, re.DOTALL
        )
        if match:
            return re.sub(r"<[^>]+>", "", match.group(1)).strip()
    except Exception as e:
        logger.error(f"Detail page error for {detail_url[:60]}: {e}")
    return ""


def fetch_preprint_links(detail_url: str, session) -> list[str]:
    """Extract pre-print (arXiv) links from the detail page."""
    try:
        resp = session.get(detail_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        return [m.group(1) for m in re.finditer(
            r'href="(https?://[^"]*arxiv[^"]*)"[^>]*>([^<]*)</a>', resp.text
        )]
    except Exception:
        return []


def fetch_doi(detail_url: str, session) -> str:
    """Extract the publisher DOI from the detail page."""
    try:
        resp = session.get(detail_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        m = re.search(r'DOI</label>.*?<a href="(https://doi\.org/10\.\d{4,}/[^"]+)"', resp.text, re.DOTALL)
        if m:
            return m.group(1)
    except Exception:
        pass
    return ""