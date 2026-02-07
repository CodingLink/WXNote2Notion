# 微信读书 → Notion ETL（中文说明）

本项目是一个可生产化的 ETL + CI/CD 自动化工具，用于：
1. 解析微信读书导出的 TXT 笔记。
2. 将笔记、书架、每日阅读活动同步到 Notion 三个数据库。
3. 按日生成 GitHub 风格的阅读热力图（SVG + HTML），可托管在 GitHub Pages 并嵌入 Notion。
4. 自动从豆瓣抓取书籍封面（带缓存、速率限制），失败则回退到 Open Library。
5. 通过 GitHub Actions 自动触发全流程（解析 → Notion 同步 → 热力图生成 → Pages 部署）。

## 🚀 快速开始

**完整部署指南请查看：[GitHub Actions 部署指南](GITHUB_ACTIONS_GUIDE.md)**

该指南包含：
- ✅ Notion 数据库创建与配置详细步骤
- ✅ GitHub Secrets 配置说明
- ✅ GitHub Pages 启用方法
- ✅ 故障排查与常见问题解决
- ✅ 日常使用流程
- ✅ 完整的部署检查清单

---

## 目录结构
- `notes/`：微信读书 TXT 输入（版本库跟踪）。
- `wechat_read/`：解析与数据模型。
- `notion/`：Notion HTTP 客户端与各仓储（书、笔记、日活、看板）。
- `viz/`：热力图生成。
- `scripts/`：入口脚本 `sync_repo.py`。
- `vercel/`：可选的 Vercel Serverless 端点。
- `.github/workflows/`：GitHub Actions 工作流。
- `site/`：热力图输出（CI 部署到 gh-pages）。

## 环境与依赖
- Python 3.10+
- 依赖：`requests`, `beautifulsoup4`, `pytest` 等（见 `requirements.txt`）。

安装：
```bash
pip install -r requirements.txt
```

## 输入格式（必须匹配微信读书 TXT 导出）
- 第一非空行：书名；第二非空行：作者（可多行）。
- 行包含 “x个笔记”。
- 章节标题为独立行。
- 笔记项以 `◆ ` 开头。
- 想法行形如 `◆ YYYY/MM/DD发表想法 ...`，后续可跟多行正文。
- 可能出现 `原文：` 块，需归为高亮文本。
- 结尾 `-- 来自微信读书`。
- 解析对空行和空白有容错。

## 中间数据模型（wechat_read/model.py）
`Note` 字段：
- `book_title`, `author`, `section_title`
- `item_type`: `highlight|thought|mixed`
- `highlight_text`, `note_text`
- `created_date`
- `source` 固定 `WeChat Read`
- `fingerprint`：用于幂等，规则：
  - 若有日期：`sha256(book_title + created_date + highlight + note)`
  - 否则：`sha256(book_title + section + highlight + note)`

每日聚合：仅当存在 `created_date` 时计数。

## Notion 三个数据库要求
A) NOTES_DB: “WeChat Read Notes”
- Title (title)
- Book (relation → BOOKS_DB)
- Section (rich_text)
- Type (select)
- Highlight (rich_text)
- Note (rich_text)
- Created Date (date)
- Source (select, 默认 "WeChat Read")
- Fingerprint (rich_text)
- Import Time (date)
- 页面内容：包含书名/章节/高亮/批注的块。

B) BOOKS_DB: “WeChat Read Bookshelf”
- Name (title)
- Author (rich_text)
- Source (select, 默认 "WeChat Read")
- CoverUrl (url)
- Last Import Time (date)
- Annual Book List（年度书单，rich_text，该书最后笔记的年份）
- Notes Count（建议 rollup，如不方便可忽略）
- 页面封面：若 Notion API 支持则设为封面 URL。

C) DAILY_DB: “Daily Reading Activity”
- Date (date, 唯一)
- Notes Count (number)
- Source (select, 默认 "WeChat Read")
- Last Import Time (date)

D) DASHBOARD_PAGE（可选）
- 页面中添加 Embed，指向热力图 URL（GitHub Pages）。
- 如需书架视图，可在 Notion 手动创建链接视图。

## 封面抓取与缓存
- **中文书籍**（自动检测中文字符）：豆瓣 → Google Books API → Open Library。
- **非中文书籍**：Open Library → Google Books API → 豆瓣。
- 豆瓣：改进抓取逻辑，多选择器支持，1 秒节流。
- Google Books：通过官方 API 获取，支持多种尺寸封面。
- 缓存：`.cache/douban_cover.json`，键为 `(title|author)`。
- 失败不会中断同步，CoverUrl 留空继续执行。

## CLI 入口（scripts/sync_repo.py）
参数：
- `--notes-dir`：TXT 目录，默认 `notes`
- `--mode`：`parse|sync|heatmap|all`，默认 `all`
- `--year`：热力图年份，默认当前年
- `--dry-run`：仅解析，不写入 Notion
- `--no-cover`：禁用封面抓取
- `--notion-token|--notes-db|--books-db|--daily-db`：覆盖环境变量

示例：
```bash
python scripts/sync_repo.py --notes-dir notes --mode all
```

环境变量优先：
- `NOTION_TOKEN`
- `NOTION_NOTES_DB`
- `NOTION_BOOKS_DB`
- `NOTION_DAILY_DB`

## GitHub Actions（已实现，推荐）
工作流：`.github/workflows/notion_sync.yml`
- 触发：对 main 分支的 push，包含 `notes/**/*.txt` 或代码变更。
- 步骤：Checkout → Setup Python → 安装依赖 → `python scripts/sync_repo.py --notes-dir notes --mode all` → 上传 `site/` → `deploy-pages`。
- 仓库 Secrets：`NOTION_TOKEN`, `NOTION_NOTES_DB`, `NOTION_BOOKS_DB`, `NOTION_DAILY_DB`。
- GitHub Pages URL：`https://<github_user>.github.io/<repo>/`。

## Vercel 方案（可选）
- 函数：`vercel/api/sync.py`，入口 `handler`。
- 环境变量：`NOTION_TOKEN`, `NOTION_NOTES_DB`, `NOTION_BOOKS_DB`, `NOTION_DAILY_DB`, `SYNC_TOKEN`。
- 调用：`GET /api/sync?token=<SYNC_TOKEN>`，可由 GitHub Webhook 或 Vercel Cron 触发。
- 逻辑：与 CLI 相同，执行同步并生成 `site/` 热力图。

## 热力图
- 生成：`viz/heatmap.py` 输出 `site/heatmap.svg` 和 `site/index.html`。
- 样式：GitHub 风格，深色卡片，悬停显示 data-* 属性可用。
- 嵌入：Notion Dashboard 中使用 Embed，指向 Pages URL。

## 测试
- 使用 pytest：`pytest`
- 示例测试：`tests/test_parser.py`，样例输入见 `tests/data/sample.txt`。

## 幂等与安全
- 指纹去重，按 Fingerprint upsert 笔记；按 Name upsert 书籍；按 Date upsert 日活。
- API 调用包含 429/5xx 重试与简单退避；单文件错误不应阻断全部流程（可根据需要加强 try/except 包裹）。

## 本地开发流程
```bash
pip install -r requirements.txt
python scripts/sync_repo.py --notes-dir notes --mode parse  # 仅解析
python scripts/sync_repo.py --notes-dir notes --mode all    # 完整同步 + 热力图
```

## 注意事项
- 请为 Notion 集成授予对应数据库的读写权限。
- 豆瓣页面结构可能变化，若封面获取失败，请检查 `.cache/douban_cover.json` 并考虑手动填充 CoverUrl。
- 若仓库开启 GitHub Pages，首次部署后再在 Notion 嵌入热力图 URL。
