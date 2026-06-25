💥**Update**: **FSE 2026** 的论文已收录！

# SE 顶会论文列表

{ICSE, FSE, ASE, ISSTA} 自 2024 年以来的研究论文。

[English](README.md)

## 快速开始

```bash
git clone https://github.com/iCSawyer/SEConfPaperList
cd SEConfPaperList
pip install requests lxml orjson python-dotenv
cp .env.sample .env          # 编辑 .env，填写 API key（可选）

# 第一步：抓取论文并补充摘要
python scrape_papers.py

# 第二步：翻译标题和摘要为中文（需要 OPENAI_API_KEY）
python translate_papers.py
```

或一步完成：

```bash
python run_pipeline.py
```

## 如何贡献

1. Fork 并 clone：`git clone https://github.com/iCSawyer/SEConfPaperList`
2. 安装依赖：`pip install requests lxml orjson python-dotenv`
3. 在 `paper_spiders/utils/paperlist.py` 中添加新的会议 URL
4. 运行：`python scrape_papers.py`
5. 提交并推送

## 脚本说明

| 脚本 | 用途 |
|------|------|
| `scrape_papers.py` | 从会议列表页抓取论文，通过 researchr 补充摘要和 arXiv 链接 |
| `translate_papers.py` | 通过 LLM API 翻译标题和摘要为中文。支持断点续翻：中断后重新运行即可继续。 |
| `run_pipeline.py` | 依次运行上述两个脚本（便捷封装） |

### 断点续翻

```bash
# 翻译所有未翻译的论文
python translate_papers.py

# 如果中断了，直接重新运行 — 已翻译的会自动跳过
python translate_papers.py

# 查看还有多少论文需要翻译
python translate_papers.py --dry-run

# 强制重新翻译所有论文
python translate_papers.py --force
```

## 环境变量

复制 `.env.sample` 为 `.env` 并填写需要的配置：

| 变量 | 必填 | 说明 |
|------|:---:|------|
| `OPENAI_API_KEY` | 翻译需要 | LLM 翻译的 API key |
| `OPENAI_BASE_URL` | 否 | 翻译 API 地址（默认 `https://api.openai.com/v1`） |
| `TRANSLATE_MODEL` | 否 | 翻译模型（默认 `gpt-4o-mini`） |

## 输出字段

| 字段 | 来源 | 说明 |
|------|------|------|
| `conf` | 配置 | 会议名称，如 "ICSE 2025" |
| `title` | 页面 | 论文标题 |
| `author` | 页面 | 作者列表 |
| `abstract` | researchr 详情页 | 论文摘要 |
| `full_version_url` | researchr 详情页 | conf.researchr.org 详情页 URL |
| `arxiv_url` | researchr 详情页 | arXiv 摘要页（有预印本时） |
| `arxiv_pdf_url` | researchr 详情页 | arXiv PDF（有预印本时） |
| `keywords` | – | 预留字段 |
| `title_cn` | LLM 翻译 | 中文标题 |
| `abstract_cn` | LLM 翻译 | 中文摘要 |
| `arxiv_id` | – | 预留字段 |
| `doi` | – | 预留字段 |
| `dblp_url` | – | 预留字段 |

## 架构

```
paperlist.py          → 会议 URL 列表
scrape_papers.py      → 抓取列表页，解析标题/作者，通过 researchr 补充数据
translate_papers.py   → 通过 LLM API 翻译标题/摘要（支持断点续翻）
papers.jsonl          → 所有数据以 JSONL 格式存储（唯一数据源）
```

## 已知限制

1. 每篇论文约需 2 个 HTTP 请求（~1.5 秒），1918 篇论文约需 48 分钟。
2. arXiv 链接仅在论文有预印本时才有。
3. FSE 2024 / ISSTA 2024 使用独立域名，爬虫已适配。### Papers