💥**Update**: **FSE 2026** 的论文已收录！

# SE 顶会论文列表

{ICSE, FSE, ASE, ISSTA} 自 2024 年以来的研究论文。

🌐 **在线浏览**: [zephyrq-z.github.io/SEConfPaperList](https://zephyrq-z.github.io/SEConfPaperList/)


[English](README.md)

## 项目结构

```
SEConfPaperList/
├── scrape_papers.py           # 抓取论文列表 + 补充摘要
├── translate_papers.py        # 翻译标题和摘要为中文
├── build_site.py              # 生成静态论文浏览网站
├── lib/                       # 共享模块
│   ├── config.py              # 会议 URL 配置
│   ├── io.py                  # JSONL 读写工具
│   ├── researchr.py           # researchr.org 摘要/arXiv 抓取
│   └── translate.py           # LLM 翻译（OpenAI 兼容 API）
├── data/                      # 输出目录
│   └── papers.jsonl           # 唯一数据源（JSONL 格式）
├── docs/                      # 静态网站
│   └── index.html             # 自包含的论文浏览 UI
├── .github/workflows/
│   └── deploy.yml             # GitHub Actions：部署到 Pages
├── .env.sample                # 环境变量模板
└── README.md / README_CN.md
```

## 数据流

```
lib/config.py (会议 URL 配置)
        │
        ▼
scrape_papers.py     ──→  data/papers.jsonl  ◀── 唯一数据源
  1. 抓取会议列表页           │
  2. 补充摘要 + arXiv        ├── translate_papers.py  → 翻译
                             │
                             └── build_site.py        → docs/index.html
                                                           │
                                                      GitHub Pages 🚀
```

## 快速开始

```bash
git clone https://github.com/iCSawyer/SEConfPaperList
cd SEConfPaperList
pip install requests lxml orjson python-dotenv
cp .env.sample .env          # 编辑 .env，填写 API key（可选）

# 抓取论文
python scrape_papers.py

# 翻译为中文（需要 OPENAI_API_KEY）
python translate_papers.py
```

## 脚本说明

| 脚本 | 作用 | 关键参数 |
|------|------|------|
| `scrape_papers.py` | 抓取所有会议论文，补充摘要和 arXiv 链接 | `--conf "ICSE 2026"`, `--limit 10`, `--output` |
| `translate_papers.py` | 翻译标题和摘要为中文，支持断点续翻 | `--input`, `--force`, `--dry-run` |
| `build_site.py` | 从 JSONL 生成静态论文浏览网站 | `--input`, `--output` |

### 测试爬取（限制模式）

```bash
python scrape_papers.py --limit 10 --conf "ICSE 2026"
```

### 断点续翻

```bash
python translate_papers.py              # 翻译未翻译的论文
python translate_papers.py --dry-run    # 查看还需翻译多少
python translate_papers.py --force      # 强制重新翻译所有
```

### 静态论文浏览网站

```bash
python build_site.py
# 打开 docs/index.html 即可
```

网站功能：侧边栏筛选、实时搜索、翻页、键盘快捷键（`←→ hjkl gG /`）、URL 哈希路由、暗色模式。

## 环境变量

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
| `full_version_url` | researchr 详情页 | 详情页 URL |
| `arxiv_url` | researchr 详情页 | arXiv 摘要页 |
| `arxiv_pdf_url` | researchr 详情页 | arXiv PDF |
| `doi` | researchr 详情页 | 出版社 DOI（如 https://doi.org/10.1145/...） |
| `title_cn` | LLM 翻译 | 中文标题 |
| `abstract_cn` | LLM 翻译 | 中文摘要 |

## 如何贡献

1. Fork 并 clone
2. 安装依赖：`pip install requests lxml orjson python-dotenv`
3. 在 `lib/config.py` 中添加新的会议 URL
4. 运行：`python scrape_papers.py`
5. 提交并推送