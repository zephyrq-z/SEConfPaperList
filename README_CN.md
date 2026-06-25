💥**Update**: **FSE 2026** 的论文已收录！

# SE 顶会论文列表

{ICSE, FSE, ASE, ISSTA} 自 2024 年以来的研究论文。

[English](README.md)

## 项目结构

```
SEConfPaperList/
├── scrape_papers.py           # 入口：抓取论文列表 + 补充摘要
├── scrape_test.py             # 测试：从指定 URL 抓取最多 10 篇论文
├── translate_papers.py        # 入口：翻译标题和摘要
├── run_pipeline.py            # 便捷封装：依次运行上述两个脚本
├── paper_spiders/
│   └── utils/
│       ├── paperlist.py       # 会议 URL 配置
│       ├── researchr.py       # 从 researchr.org 抓取摘要和 arXiv 链接
│       └── translate.py       # LLM 翻译（OpenAI 兼容 API）
├── data/                      # 输出目录
│   ├── papers.jsonl           # 唯一数据源（JSONL 格式）
│   ├── papers.json            # 按会议分组的 JSON（由 jsonl_to_json.py 生成）
│   ├── papers.md              # Markdown 表格（生成产物）
│   └── test_papers.jsonl      # 测试爬取结果（由 scrape_test.py 生成）
├── .env.sample                # 环境变量模板
└── README.md / README_CN.md
```

## 数据流

```
paperlist.py (会议 URL 配置)
        │
        ▼
scrape_papers.py
  1. 抓取会议列表页 → 标题 + 作者
  2. 调用 researchr.py → 补充摘要 + arXiv 链接
        │
        ▼
data/papers.jsonl  ◀── 唯一数据源，所有脚本读/写此文件
        │
        ├── translate_papers.py → 翻译 title_cn / abstract_cn
        │                              （写入同一个 papers.jsonl）
        │
        └── jsonl_to_json.py   → data/papers.json（按会议分组）
```

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

## 文件说明

| 文件 | 作用 | 读 | 写 |
|------|------|:---:|:---:|
| `scrape_papers.py` | 从会议列表页抓取论文，通过 researchr 补充摘要和 arXiv 链接 | `paperlist.py` | `data/papers.jsonl` |
| `scrape_test.py` | 测试爬取：从文件中配置的 URL 抓取指定数量（默认 10 篇）论文 | — | `data/test_papers.jsonl` |
| `translate_papers.py` | 通过 LLM API 翻译标题和摘要为中文。支持断点续翻 | `data/papers.jsonl` | `data/papers.jsonl` |
| `run_pipeline.py` | 依次运行 scrape → translate（便捷封装） | — | — |
| `jsonl_to_json.py` | 将 papers.jsonl 按会议分组导出为 JSON | `data/papers.jsonl` | `data/papers.json` |
### 测试爬取

```bash
# 修改 scrape_test.py 顶部的配置后运行：
python scrape_test.py
```

脚本会打印每篇论文的标题、作者、摘要前 120 字和 arXiv 链接，结果保存到 `data/test_papers.jsonl`。

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

所有字段存储在 `data/papers.jsonl`（每行一个 JSON 对象）：

| 字段 | 来源 | 说明 |
|------|------|------|
| `conf` | 配置 | 会议名称，如 "ICSE 2025" |
| `title` | 列表页 | 论文标题 |
| `author` | 列表页 | 作者列表 |
| `abstract` | researchr 详情页 | 论文摘要 |
| `full_version_url` | researchr 详情页 | conf.researchr.org 详情页 URL |
| `arxiv_url` | researchr 详情页 | arXiv 摘要页（有预印本时） |
| `arxiv_pdf_url` | researchr 详情页 | arXiv PDF（有预印本时） |
| `title_cn` | LLM 翻译 | 中文标题 |
| `abstract_cn` | LLM 翻译 | 中文摘要 |
| `keywords` | – | 预留字段 |
| `arxiv_id` | – | 预留字段 |
| `doi` | – | 预留字段 |
| `dblp_url` | – | 预留字段 |

## 如何贡献

1. Fork 并 clone：`git clone https://github.com/iCSawyer/SEConfPaperList`
2. 安装依赖：`pip install requests lxml orjson python-dotenv`
3. 在 `paper_spiders/utils/paperlist.py` 中添加新的会议 URL
4. 运行：`python scrape_papers.py`
5. 提交并推送

## 已知限制

1. 每篇论文约需 2 个 HTTP 请求（~1.5 秒），1918 篇论文约需 48 分钟。
2. arXiv 链接仅在论文有预印本时才有。
3. FSE 2024 / ISSTA 2024 使用独立域名，爬虫已适配。