"""LLM translation for paper titles and abstracts (OpenAI-compatible API)."""

import os
import json
import time
import logging
import urllib.request
import urllib.error
from typing import Optional

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gpt-4o-mini"
MAX_RETRIES = 5


def _get_api_config() -> tuple[str, str, str]:
    api_key = os.environ.get("OPENAI_API_KEY", "")
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
    model = os.environ.get("TRANSLATE_MODEL", DEFAULT_MODEL)
    return api_key, base_url, model


def _call_llm(messages: list[dict], api_key: str, base_url: str, model: str) -> Optional[str]:
    url = f"{base_url}/chat/completions"
    payload = json.dumps({
        "model": model, "messages": messages,
        "temperature": 0.3, "max_tokens": 4096,
    }).encode("utf-8")

    for attempt in range(MAX_RETRIES):
        try:
            req = urllib.request.Request(url, data=payload)
            req.add_header("Content-Type", "application/json")
            req.add_header("Authorization", f"Bearer {api_key}")
            resp = urllib.request.urlopen(req, timeout=120)
            return json.loads(resp.read().decode("utf-8"))["choices"][0]["message"]["content"].strip()
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8") if e.fp else ""
            logger.error(f"LLM HTTP {e.code}: {body[:200]}")
            if e.code == 429:
                delay = 10 * (2 ** attempt)
                logger.warning(f"Rate limited, retrying in {delay}s (attempt {attempt+1}/{MAX_RETRIES})...")
                time.sleep(delay)
                continue
            return None
        except Exception as e:
            delay = 5 * (2 ** attempt)
            logger.warning(f"LLM error, retrying in {delay}s (attempt {attempt+1}/{MAX_RETRIES}): {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(delay)
            else:
                return None
    return None


SYSTEM_PROMPT = (
    "You are a professional translator. "
    "Translate the following English academic paper title and abstract into Simplified Chinese. "
    "Output ONLY the translation in this format:\n"
    "Title: <Chinese title>\n"
    "Abstract: <Chinese abstract>\n"
    "Keep technical terms (like LLM, API, Python, GitHub) in English. "
    "Keep proper nouns in English."
)


def _translate_one(item: dict, api_key: str, base_url: str, model: str) -> None:
    """Translate a single paper's title and abstract."""
    title = item.get("title", "")
    abstract = item.get("abstract", "")

    if not title:
        item["title_cn"] = ""
        item["abstract_cn"] = ""
        return

    user = f"Title: {title}"
    if abstract:
        user += f"\n\nAbstract: {abstract}"

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user},
    ]

    result = _call_llm(messages, api_key, base_url, model)
    if not result:
        item["title_cn"] = ""
        item["abstract_cn"] = ""
        return

    title_cn = ""
    abstract_cn = ""
    in_abstract = False
    for line in result.strip().split("\n"):
        if line.startswith("Title:"):
            title_cn = line[6:].strip()
        elif line.startswith("标题"):
            title_cn = line.split(":", 1)[1].strip() if ":" in line else line.split(":", 1)[-1].strip()
        elif line.startswith("Abstract:"):
            in_abstract = True
            abstract_cn = line[9:].strip()
        elif line.startswith("摘要"):
            in_abstract = True
            abstract_cn = line.split(":", 1)[1].strip() if ":" in line else ""
        elif in_abstract and line.strip():
            abstract_cn += " " + line.strip()

    if not title_cn:
        title_cn = result.strip().split("\n")[0].strip()

    item["title_cn"] = title_cn
    item["abstract_cn"] = abstract_cn


def translate_batch(items: list[dict], api_key: str = "", base_url: str = "", model: str = "") -> list[dict]:
    """Translate a batch of papers one by one."""
    if not api_key:
        api_key, base_url, model = _get_api_config()
    for item in items:
        _translate_one(item, api_key, base_url, model)
    return items