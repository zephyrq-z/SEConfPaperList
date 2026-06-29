💥**Update**: **FSE 2026** papers are now included!

# SE Conference Paper List

Research papers from {ICSE, FSE, ASE, ISSTA} since 2024.

🌐 **Online**: [zephyrq-z.github.io/SEConfPaperList](https://zephyrq-z.github.io/SEConfPaperList/)


[中文](README_CN.md)

## Project Structure

```
SEConfPaperList/
├── scrape_papers.py           # Scrape paper listings + enrich with metadata
├── translate_papers.py        # Translate titles and abstracts to Chinese
├── build_site.py              # Generate static paper browsing site
├── lib/                       # Shared modules
│   ├── config.py              # Conference URL configuration
│   ├── io.py                  # JSONL read/write helpers
│   ├── researchr.py           # researchr.org abstract / arXiv scraping
│   └── translate.py           # LLM translation (OpenAI-compatible API)
├── data/                      # Output directory
│   └── papers.jsonl           # Canonical data source (JSONL format)
├── docs/                      # Static site
│   └── index.html             # Self-contained paper browsing UI
├── .github/workflows/
│   └── deploy.yml             # GitHub Actions: deploy to Pages
├── .env.sample                # Environment variable template
└── README.md / README_CN.md
```

## Data Flow

```
lib/config.py (conference URLs)
        │
        ▼
scrape_papers.py     ──→  data/papers.jsonl  ◀── Canonical data source
  1. Scrape listings           │
  2. Enrich abstracts          ├── translate_papers.py  → Chinese translation
     + arXiv links             │
                               └── build_site.py        → docs/index.html
                                                             │
                                                        GitHub Pages 🚀
```

## Quick Start

```bash
git clone https://github.com/iCSawyer/SEConfPaperList
cd SEConfPaperList
pip install requests lxml orjson python-dotenv
cp .env.sample .env          # edit .env, fill in API key (optional)

# Scrape papers
python scrape_papers.py

# Translate to Chinese (requires OPENAI_API_KEY)
python translate_papers.py
```

## Scripts

| Script | Purpose | Key flags |
|--------|---------|-----------|
| `scrape_papers.py` | Scrape all conferences, enrich with abstracts & arXiv links | `--conf "ICSE 2026"`, `--limit 10`, `--output` |
| `translate_papers.py` | Translate titles & abstracts to Chinese, with resume support | `--input`, `--force`, `--dry-run` |
| `build_site.py` | Generate a static paper browsing SPA from JSONL | `--input`, `--output` |

### Test Scrape (limit mode)

```bash
python scrape_papers.py --limit 10 --conf "ICSE 2026"
```

### Translation (Chinese)

Requires an OpenAI-compatible API key. Set it in `.env`:

```bash
cp .env.sample .env
# edit .env: fill in OPENAI_API_KEY (and optionally OPENAI_BASE_URL, TRANSLATE_MODEL)
```

```bash
python translate_papers.py              # translate untranslated papers (resumable)
python translate_papers.py --dry-run    # preview how many need translation
python translate_papers.py --force      # clear all + re-translate everything
```

### Static Paper Browser

```bash
python build_site.py
# Open docs/index.html in your browser
```

Features: sidebar filtering, live search, prev/next navigation, keyboard shortcuts (`←→ hjkl gG /`), URL hash routing, dark mode.

## Environment Variables

| Variable | Required | Description |
|----------|:--------:|-------------|
| `OPENAI_API_KEY` | For translation | LLM API key |
| `OPENAI_BASE_URL` | No | API base URL (default `https://api.openai.com/v1`) |
| `TRANSLATE_MODEL` | No | Model name (default `gpt-4o-mini`) |

## Output Fields

All fields stored in `data/papers.jsonl` (one JSON object per line):

| Field | Source | Description |
|-------|--------|-------------|
| `conf` | Config | Conference name, e.g. "ICSE 2025" |
| `title` | Listing page | Paper title |
| `author` | Listing page | Author list |
| `abstract` | researchr detail page | Paper abstract |
| `full_version_url` | researchr detail page | Detail page URL |
| `arxiv_url` | researchr detail page | arXiv abstract page |
| `arxiv_pdf_url` | researchr detail page | arXiv PDF |
| `doi` | researchr detail page | Publisher DOI (e.g. https://doi.org/10.1145/...) |
| `title_cn` | LLM translation | Chinese title |
| `abstract_cn` | LLM translation | Chinese abstract |

## Contributing

1. Fork and clone
2. Install dependencies: `pip install requests lxml orjson python-dotenv`
3. Add new conference URLs in `lib/config.py`
4. Run: `python scrape_papers.py`
5. Commit and push