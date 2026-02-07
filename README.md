# WeChat Read → Notion ETL

Production-ready ETL that parses WeChat Read TXT exports, syncs them into three Notion databases, fetches book covers from Douban with safe fallbacks, and publishes a GitHub-like daily activity heatmap to GitHub Pages.

## 🚀 Quick Start

**For complete deployment guide, see: [GitHub Actions Deployment Guide](GITHUB_ACTIONS_GUIDE.md)**

The guide includes:
- ✅ Step-by-step Notion database setup
- ✅ GitHub Secrets configuration
- ✅ GitHub Pages setup
- ✅ Troubleshooting & FAQ
- ✅ Daily usage workflow
- ✅ Complete deployment checklist

---

## Components
- Parser: resilient TXT parser in [wechat_read/parser.py](wechat_read/parser.py) with [wechat_read/model.py](wechat_read/model.py).
- Notion sync: HTTP-only client [notion/client.py](notion/client.py) plus repositories for books, notes, and daily stats.
- Cover fetcher: Douban-first with Open Library fallback and disk cache in `.cache/douban_cover.json`.
- Heatmap: SVG + HTML generator in [viz/heatmap.py](viz/heatmap.py) outputs to `site/`.
- Entrypoint: [scripts/sync_repo.py](scripts/sync_repo.py) (CLI) and [vercel/api/sync.py](vercel/api/sync.py) (serverless).
- CI/CD: [\.github/workflows/notion_sync.yml](.github/workflows/notion_sync.yml) runs on pushes and deploys GitHub Pages.

## Notion setup
Create three databases in Notion and copy their IDs as secrets.

**NOTES_DB: "WeChat Read Notes"**
- Title (title)
- Book (relation → BOOKS_DB)
- Section (rich_text)
- Type (select; values: highlight, thought, mixed)
- Highlight (rich_text)
- Note (rich_text)
- Created Date (date)
- Source (select; default "WeChat Read")
- Fingerprint (rich_text)
- Import Time (date)

**BOOKS_DB: "WeChat Read Bookshelf"**
- Name (title)
- Author (rich_text)
- Source (select; default "WeChat Read")
- CoverUrl (url)
- Last Import Time (date)
- Annual Book List (rich_text)
- Optional: Notes Count (number or rollup)

Dashboard: create a page and add an Embed block pointing to the heatmap URL (see GitHub Pages URL below). Linked views of BOOKS_DB can be added manually if desired.

## Environment variables / secrets
- NOTION_TOKEN: integration token with database access
- NOTION_NOTES_DB: Notes database ID
- NOTION_BOOKS_DB: Books database ID
- NOTION_DAILY_DB: Daily database ID
- SYNC_TOKEN (Vercel optional): shared secret for serverless endpoint

## Local usage
Install deps, then run the CLI.
```bash
pip install -r requirements.txt
python scripts/sync_repo.py --notes-dir notes --mode all
```
Flags: `--mode parse|sync|heatmap|all`, `--dry-run`, `--year YYYY`, `--no-cover`.

## GitHub Actions (Option A - implemented)
Workflow [\.github/workflows/notion_sync.yml](.github/workflows/notion_sync.yml):
- Triggers on pushes touching TXT files or code.
- Steps: checkout → setup Python → install deps → run sync (`python scripts/sync_repo.py --mode all`) → upload `site/` → deploy to GitHub Pages.
- Configure repository secrets: NOTION_TOKEN, NOTION_NOTES_DB, NOTION_BOOKS_DB, NOTION_DAILY_DB.
- Heatmap URL after first deploy: `https://<github_user>.github.io/<repo>/`.

## Vercel (Option B - alternative)
Deploy [vercel/api/sync.py](vercel/api/sync.py) as a Python serverless function. Set env vars (NOTION_*, SYNC_TOKEN). Trigger with `GET /api/sync?token=<SYNC_TOKEN>` via GitHub webhook or Vercel cron. Same logic runs sync + heatmap generation.

## Cover fetching
- **Chinese books** (detected by Chinese characters): Douban → Google Books API → Open Library.
- **Non-Chinese books**: Open Library → Google Books API → Douban.
- Douban: improved scraping with multiple selectors and 1 req/sec rate limit.
- Cache: `.cache/douban_cover.json` keyed by `(title|author)`.
- If all sources fail, CoverUrl remains empty; sync continues.

## Heatmap output
- Generated files: `site/heatmap.svg` and `site/index.html`.
- Embed the GitHub Pages URL in Notion dashboard.

## Tests
Parser unit test lives in [tests/test_parser.py](tests/test_parser.py) using sample TXT in [tests/data/sample.txt](tests/data/sample.txt).

## Example TXT format
See [notes/sample_input.txt](notes/sample_input.txt). Parsing rules tolerate blank lines, section headings, "◆ " bullets, optional "原文：" blocks, and footer `-- 来自微信读书`.
