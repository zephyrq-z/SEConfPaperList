"""
Chinese translation utility for paper titles and abstracts.

Uses an LLM API (OpenAI-compatible) to translate English text to Chinese.
Set the environment variable OPENAI_API_KEY to use this module.
Set OPENAI_BASE_URL for custom API endpoints (default: https://api.openai.com/v1)
"""

import os
import json
import re
import time
import logging
import urllib.request
import urllib.error
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_MODEL = "gpt-4o-mini"
MAX_RETRIES = 3
BATCH_SIZE = 10  # Number of items to translate in one API call


def _get_api_config():
    """Get API configuration from environment variables."""
    api_key = os.environ.get("OPENAI_API_KEY", "")
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
    model = os.environ.get("TRANSLATE_MODEL", DEFAULT_MODEL)
    return api_key, base_url, model


def _call_llm(messages: List[Dict], api_key: str, base_url: str, model: str) -> Optional[str]:
    """Call the LLM API with retries."""
    url = f"{base_url}/chat/completions"

    payload = json.dumps({
        "model": model,
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": 4096,
    }).encode("utf-8")

    for attempt in range(MAX_RETRIES):
        try:
            req = urllib.request.Request(url, data=payload)
            req.add_header("Content-Type", "application/json")
            req.add_header("Authorization", f"Bearer {api_key}")

            response = urllib.request.urlopen(req, timeout=60)
            result = json.loads(response.read().decode("utf-8"))
            return result["choices"][0]["message"]["content"].strip()
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8") if e.fp else ""
            logger.error(f"LLM API HTTP error {e.code}: {error_body[:200]}")
            if e.code == 429:  # Rate limit
                time.sleep(2 ** attempt)
                continue
            return None
        except Exception as e:
            logger.error(f"LLM API error (attempt {attempt+1}): {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(1)
            else:
                return None

    return None


def translate_text(text: str, api_key: str = "", base_url: str = "", model: str = "") -> Optional[str]:
    """Translate a single English text to Chinese.

    Args:
        text: The English text to translate
        api_key: OpenAI API key (defaults to env var)
        base_url: API base URL (defaults to env var)
        model: Model name (defaults to env var)

    Returns:
        Chinese translation or None if failed
    """
    if not api_key:
        api_key, base_url, model = _get_api_config()
    else:
        base_url = base_url or os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
        model = model or os.environ.get("TRANSLATE_MODEL", DEFAULT_MODEL)

    if not api_key:
        logger.warning("No OPENAI_API_KEY set, skipping translation")
        return None

    messages = [
        {
            "role": "system",
            "content": "You are a professional translator. Translate the following academic text from English to Simplified Chinese. Only output the translation, nothing else. Keep technical terms in English where appropriate.",
        },
        {"role": "user", "content": text},
    ]

    return _call_llm(messages, api_key, base_url, model)


def translate_batch(
    items: List[Dict[str, str]], api_key: str = "", base_url: str = "", model: str = ""
) -> List[Dict[str, str]]:
    """Translate a batch of titles and abstracts in one API call.

    Args:
        items: List of dicts with 'title' and optionally 'abstract' keys
        api_key: OpenAI API key
        base_url: API base URL
        model: Model name

    Returns:
        List of dicts with 'title_cn' and 'abstract_cn' keys added
    """
    if not api_key:
        api_key, base_url, model = _get_api_config()
    else:
        base_url = base_url or os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
        model = model or os.environ.get("TRANSLATE_MODEL", DEFAULT_MODEL)

    if not api_key:
        logger.warning("No OPENAI_API_KEY set, skipping translation")
        return items

    results = []
    for i in range(0, len(items), BATCH_SIZE):
        batch = items[i : i + BATCH_SIZE]
        batch_results = _translate_single_batch(batch, api_key, base_url, model)
        results.extend(batch_results)

    return results


def _translate_single_batch(
    batch: List[Dict[str, str]], api_key: str, base_url: str, model: str
) -> List[Dict[str, str]]:
    """Translate a single batch of items."""
    # Build the input
    input_items = []
    for idx, item in enumerate(batch):
        entry = {
            "id": idx,
            "title": item.get("title", ""),
        }
        if item.get("abstract"):
            entry["abstract"] = item["abstract"]
        input_items.append(entry)

    input_json = json.dumps(input_items, ensure_ascii=False, indent=2)

    messages = [
        {
            "role": "system",
            "content": """You are a professional translator of academic computer science papers.
Translate the given English titles and abstracts into Simplified Chinese.
For each item, output a JSON object with:
- "id": the original item id
- "title_cn": Chinese translation of the title
- "abstract_cn": Chinese translation of the abstract (if present)

Rules:
1. Keep technical terms (like "LLM", "API", "Python", "GitHub") in English
2. Keep proper nouns in English
3. Use natural, academic Chinese phrasing
4. Output ONLY the JSON array, nothing else""",
        },
        {"role": "user", "content": input_json},
    ]

    result = _call_llm(messages, api_key, base_url, model)
    if not result:
        # Return items with empty translations
        for item in batch:
            item["title_cn"] = ""
            item["abstract_cn"] = ""
        return batch

    try:
        # Try to parse the JSON response
        # Strip markdown code blocks if present
        cleaned = result.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```\w*\n?", "", cleaned)
            cleaned = re.sub(r"\n```$", "", cleaned)

        translations = json.loads(cleaned)
        translation_map = {t["id"]: t for t in translations}

        for item in batch:
            idx = batch.index(item)
            if idx in translation_map:
                item["title_cn"] = translation_map[idx].get("title_cn", "")
                item["abstract_cn"] = translation_map[idx].get("abstract_cn", "")
            else:
                item["title_cn"] = ""
                item["abstract_cn"] = ""

    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logger.error(f"Failed to parse translation response: {e}")
        logger.debug(f"Raw response: {result[:500]}")
        # Fallback: translate items individually
        for item in batch:
            item["title_cn"] = translate_text(item.get("title", ""), api_key, base_url, model) or ""
            if item.get("abstract"):
                item["abstract_cn"] = (
                    translate_text(item["abstract"], api_key, base_url, model) or ""
                )
            else:
                item["abstract_cn"] = ""

    return batch