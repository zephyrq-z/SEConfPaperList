"""LLM translation for paper titles and abstracts (OpenAI-compatible API)."""

import os
import json
import re
import time
import logging
import urllib.request
import urllib.error
from typing import Optional

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gpt-4o-mini"
MAX_RETRIES = 5
BATCH_SIZE = 10


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


def _extract_json_array(text: str) -> Optional[str]:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*\n?", "", cleaned)
    cleaned = re.sub(r"\n?```\s*$", "", cleaned)
    start = cleaned.find("[")
    if start < 0:
        return None
    depth = 0
    for i in range(start, len(cleaned)):
        if cleaned[i] == "[":
            depth += 1
        elif cleaned[i] == "]":
            depth -= 1
            if depth == 0:
                return cleaned[start:i + 1]
    return None


def translate_batch(items: list[dict], api_key: str = "", base_url: str = "", model: str = "") -> list[dict]:
    """Translate a batch of titles and abstracts. Adds 'title_cn' and 'abstract_cn'."""
    if not api_key:
        api_key, base_url, model = _get_api_config()
    else:
        base_url = base_url or os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
        model = model or os.environ.get("TRANSLATE_MODEL", DEFAULT_MODEL)

    if not api_key:
        logger.warning("No OPENAI_API_KEY set, skipping translation")
        return items

    for i in range(0, len(items), BATCH_SIZE):
        batch = items[i:i + BATCH_SIZE]
        _translate_batch(batch, api_key, base_url, model)
    return items


def _translate_batch(batch: list[dict], api_key: str, base_url: str, model: str) -> None:
    input_items = [{"id": idx, "title": item.get("title", "")} for idx, item in enumerate(batch)]
    for idx, item in enumerate(batch):
        if item.get("abstract"):
            input_items[idx]["abstract"] = item["abstract"]

    messages = [
        {"role": "system", "content": """You are a professional translator of academic computer science papers.
Translate the given English titles and abstracts into Simplified Chinese.
For each item, output a JSON object with:
- "id": the original item id
- "title_cn": Chinese translation of the title
- "abstract_cn": Chinese translation of the abstract (if present)

Rules:
1. Keep technical terms (like "LLM", "API", "Python", "GitHub") in English
2. Keep proper nouns in English
3. Use natural, academic Chinese phrasing
4. Output ONLY the JSON array, nothing else"""},
        {"role": "user", "content": json.dumps(input_items, ensure_ascii=False, indent=2)},
    ]

    result = _call_llm(messages, api_key, base_url, model)
    if not result:
        for item in batch:
            item["title_cn"] = ""
            item["abstract_cn"] = ""
        return

    try:
        cleaned = _extract_json_array(result)
        if not cleaned:
            raise ValueError("No JSON array in response")
        translations = json.loads(cleaned)
        tmap = {t["id"]: t for t in translations}
        for idx, item in enumerate(batch):
            if idx in tmap:
                item["title_cn"] = tmap[idx].get("title_cn", "")
                item["abstract_cn"] = tmap[idx].get("abstract_cn", "")
            else:
                item["title_cn"] = ""
                item["abstract_cn"] = ""
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
        logger.error(f"Failed to parse translation: {e}")
        for item in batch:
            item["title_cn"] = ""
            item["abstract_cn"] = ""