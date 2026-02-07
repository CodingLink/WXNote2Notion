# GitHub Actions 自动化部署完整指南

本指南将帮助你配置 GitHub Actions，实现微信读书笔记自动同步到 Notion 并生成热力图。

---

## 📋 前置准备

### 1. Notion 配置

#### 1.1 创建 Notion Integration
1. 访问 https://www.notion.so/my-integrations
2. 点击 **"+ New integration"**
3. 填写信息：
   - Name: `WeChat Read Sync`（可自定义）
   - Associated workspace: 选择你的工作区
   - Type: Internal Integration
4. 点击 **Submit**
5. **复制 Internal Integration Token**（形如 `secret_xxxx...`），后续会用到

#### 1.2 创建三个 Notion 数据库

**数据库 1: WeChat Read Notes（笔记库）**
- 点击 Notion 左侧 **"+ New Page"** → **Database** → **Full page**
- 命名为 `WeChat Read Notes`
- 添加以下属性（Properties）：

| 属性名 | 类型 | 说明 |
|--------|------|------|
| Title | Title | 标题（默认） |
| Book | Relation | 关联到 Bookshelf 数据库 |
| Section | Rich Text | 章节名 |
| Type | Select | 选项：highlight / thought / mixed |
| Highlight | Rich Text | 高亮文本 |
| Note | Rich Text | 笔记内容 |
| Created Date | Date | 笔记创建日期 |
| Source | Select | 默认值：WeChat Read |
| Fingerprint | Rich Text | 唯一标识 |
| Import Time | Date | 导入时间 |

**数据库 2: WeChat Read Bookshelf（书架库）**
- 创建新数据库，命名为 `WeChat Read Bookshelf`
- 添加以下属性：

| 属性名 | 类型 | 说明 |
|--------|------|------|
| Name | Title | 书名（默认） |
| Author | Rich Text | 作者 |
| Source | Select | 默认值：WeChat Read |
| CoverUrl | URL | 封面图链接 |
| Last Import Time | Date | 最后导入时间 |
| Annual Book List | Rich Text | 该书最后笔记的年份 |

**数据库 3: Daily Reading Activity（日活库）**
- 创建新数据库，命名为 `Daily Reading Activity`
- 添加以下属性：

| 属性名 | 类型 | 说明 |
|--------|------|------|
| Date | Date | 日期（唯一） |
| Notes Count | Number | 笔记数量 |
| Source | Select | 默认值：WeChat Read |
| Last Import Time | Date | 最后导入时间 |

#### 1.3 为数据库授权 Integration
对于上述三个数据库，**每个都需要**：
1. 打开数据库页面
2. 点击右上角 **"⋯"** → **"Add connections"**
3. 选择刚才创建的 Integration（`WeChat Read Sync`）
4. 点击 **Confirm**

#### 1.4 获取数据库 ID
对于每个数据库：
1. 打开数据库页面
2. 点击右上角 **"⋯"** → **"Copy link"**
3. 复制的链接格式如下：
   ```
   https://www.notion.so/<workspace>/<database_name>?v=<view_id>&pvs=...
   ```
4. 从链接中提取 32 位数据库 ID：
   - 在 `<database_name>` 后面、`?v=` 前面的部分
   - 去掉所有中划线 `-`
   - 例如：`https://notion.so/myworkspace/abc123def456` → 数据库 ID 为 `abc123def456`（实际是 32 位）

记录下三个数据库的 ID：
- `NOTION_NOTES_DB` = Notes 数据库 ID
- `NOTION_BOOKS_DB` = Bookshelf 数据库 ID
- `NOTION_DAILY_DB` = Daily 数据库 ID

---

## 🚀 GitHub 仓库配置

### 2. 初始化仓库

#### 2.1 创建仓库
1. 在 GitHub 创建新仓库（可以是私有或公开）
2. 推送本项目代码到仓库：
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/你的用户名/仓库名.git
   git push -u origin main
   ```

#### 2.2 添加笔记文件
将微信读书导出的 TXT 文件放入 `notes/` 目录：
```bash
notes/
  └── 书籍1.txt
  └── 书籍2.txt
```

提交并推送：
```bash
git add notes/
git commit -m "Add reading notes"
git push
```

### 3. 配置 GitHub Secrets

1. 进入仓库页面
2. 点击 **Settings** → **Secrets and variables** → **Actions**
3. 点击 **"New repository secret"**

依次添加以下 Secrets：

| Secret 名称 | 值 | 说明 |
|-------------|-----|------|
| `NOTION_TOKEN` | `secret_xxxx...` | Notion Integration Token |
| `NOTION_NOTES_DB` | `abc123...` | Notes 数据库 ID（32位） |
| `NOTION_BOOKS_DB` | `def456...` | Bookshelf 数据库 ID（32位） |
| `NOTION_DAILY_DB` | `ghi789...` | Daily 数据库 ID（32位） |

**重要提示**：
- Secret 名称必须完全匹配（区分大小写）
- 数据库 ID 不包含中划线
- Token 以 `secret_` 开头

### 4. 启用 GitHub Pages

#### 4.1 配置 Pages
1. 进入仓库 **Settings** → **Pages**
2. Source 选择 **"GitHub Actions"**（不是 Deploy from a branch）
3. 保存设置

#### 4.2 获取 Pages URL
配置完成后，GitHub 会显示你的 Pages URL：
```
https://你的用户名.github.io/仓库名/
```
这个 URL 就是热力图的访问地址。

---

## ⚙️ 工作流配置

工作流文件已包含在项目中：`.github/workflows/notion_sync.yml`

### 工作流触发条件
自动触发于：
- 推送到 `main` 分支
- 修改了以下路径的文件：
  - `notes/**/*.txt`（笔记文件）
  - `wechat_read/**`（解析代码）
  - `notion/**`（Notion 同步代码）
  - `viz/**`（热力图生成代码）
  - `scripts/**`（脚本）
  - `.github/workflows/notion_sync.yml`（工作流本身）

手动触发：
- 进入仓库 **Actions** 标签
- 选择 **Notion Sync** 工作流
- 点击 **"Run workflow"** → **"Run workflow"**

### 工作流执行步骤
1. **Checkout**：检出代码
2. **Set up Python**：安装 Python 3.10
3. **Install dependencies**：安装依赖（requests、beautifulsoup4、pytest）
4. **Run sync**：执行同步脚本（使用 `--no-cover` 跳过封面抓取以加速同步）
   - 解析 `notes/` 目录下的 TXT 文件
   - 同步笔记到 Notion 三个数据库
   - 生成热力图到 `site/` 目录
5. **Upload site artifact**：上传 `site/` 目录为构建产物
6. **Deploy to GitHub Pages**：部署热力图到 Pages

---

## 📊 验证部署

### 5. 检查工作流执行

#### 5.1 查看运行状态
1. 进入仓库 **Actions** 标签
2. 找到最新的 **Notion Sync** 运行
3. 点击查看详细日志

#### 5.2 成功标志
日志中应出现：
```
Parsed X notes across Y files
Upserted Z books
Upserted X notes
Upserted N daily activity rows
Generated heatmap in site
```

#### 5.3 检查 Notion
- 打开 Notion 三个数据库
- 确认数据已同步
- 在 Bookshelf 数据库检查 Annual Book List 字段是否正确显示年份
- 如启用了封面抓取，可在 Gallery 视图检查书籍封面

#### 5.4 访问热力图
在浏览器访问：
```
https://你的用户名.github.io/仓库名/
```
应显示阅读活动热力图，可以用下拉框切换年份。

---

## 🔧 故障排查

### 常见问题

#### 问题 1: ModuleNotFoundError: No module named 'notion'
**原因**：Python 无法找到项目模块

**解决**：
1. 确认 workflow 文件中包含 `PYTHONPATH: ${{ github.workspace }}`
2. 检查项目根目录是否包含 `notion/`、`wechat_read/`、`viz/` 目录
3. 重新推送代码触发工作流

#### 问题 2: 工作流失败，提示 "Missing Notion config"
**原因**：Secrets 配置不正确

**解决**：
1. 检查 Secrets 名称是否完全匹配（区分大小写）
2. 确认四个 Secrets 都已添加
3. 重新获取 Token 和数据库 ID

#### 问题 3: Notion API error 404
**原因**：数据库 ID 错误或未授权

**解决**：
1. 重新获取数据库 ID（去掉中划线）
2. 确认数据库已 **Add connections** 给 Integration
3. 等待几分钟后重试

#### 问题 4: Notion API error 400 "property not exists"
**原因**：数据库属性缺失或名称不匹配

**解决**：
1. 检查数据库属性名称（区分大小写、空格）
2. 参照上方表格补充缺失的属性
3. 重新授权 Integration（右上角 "Add connections"）

#### 问题 5: GitHub Pages 404
**原因**：Pages 未正确配置

**解决**：
1. 确认 Settings → Pages → Source 选择了 **"GitHub Actions"**
2. 等待首次部署完成（查看 Actions 标签）
3. 手动触发一次工作流

#### 问题 6: 封面图未显示
**原因**：默认工作流使用 `--no-cover` 不抓取封面

**解决**：
1. 如需启用封面抓取，参考"进阶配置"章节移除 `--no-cover` 参数
2. 本地测试：`python testCover.py`
3. 检查 `.cache/douban_cover.json` 缓存
4. 考虑手动在 Notion 设置封面（CoverUrl 列填写 URL）

---

## 🎨 嵌入热力图到 Notion

### 6. 在 Notion 中嵌入热力图

#### 方式 1：嵌入到书架数据库顶部
1. 打开 **WeChat Read Bookshelf** 数据库
2. 右上角点击 **"Open as page"**
3. 在页面顶部点击空行
4. 输入 `/embed`，选择 **Embed**
5. 粘贴 Pages URL：`https://你的用户名.github.io/仓库名/`
6. 按回车

#### 方式 2：嵌入到日活数据库顶部
1. 打开 **Daily Reading Activity** 数据库
2. 同样操作，嵌入热力图

#### 方式 3：创建 Dashboard 页面
1. 创建新页面 **WeChat Read Dashboard**
2. 添加 Embed 嵌入热力图
3. 添加 Linked View 引用三个数据库（可选）

---

## 🔄 日常使用

### 添加新笔记
1. 将新的 TXT 文件放入 `notes/` 目录
2. 提交并推送：
   ```bash
   git add notes/
   git commit -m "Add new notes"
   git push
   ```
3. GitHub Actions 自动触发同步

### 更新现有笔记
1. 修改 `notes/` 目录中的 TXT 文件
2. 提交并推送
3. 幂等性保证：
   - 已存在的笔记不会重复创建（通过 Fingerprint 去重）
   - 书籍信息会更新（封面、作者、最后导入时间）
   - 日活数据会更新计数

### 查看历史数据
- Notion 数据库中保留所有历史记录
- 热力图自动包含所有年份（下拉框切换）
- GitHub Actions 保留 90 天的运行日志

---

## 📚 进阶配置

### 启用封面抓取（需要时）
默认工作流使用 `--no-cover` 跳过封面抓取以加速同步。如需启用，编辑 `.github/workflows/notion_sync.yml`，移除 `--no-cover`：
```yaml
- name: Run sync
  env:
    NOTION_TOKEN: ${{ secrets.NOTION_TOKEN }}
    NOTION_NOTES_DB: ${{ secrets.NOTION_NOTES_DB }}
    NOTION_BOOKS_DB: ${{ secrets.NOTION_BOOKS_DB }}
    NOTION_DAILY_DB: ${{ secrets.NOTION_DAILY_DB }}
  run: |
    python scripts/sync_repo.py --notes-dir notes --mode all
```

### 仅生成热力图（不同步 Notion）
```yaml
run: |
  python scripts/sync_repo.py --notes-dir notes --mode heatmap
```

### 定时触发（每天自动运行）
在工作流的 `on:` 部分添加：
```yaml
on:
  push:
    branches: [ main ]
    paths:
      - 'notes/**/*.txt'
      - ...
  schedule:
    - cron: '0 0 * * *'  # 每天 UTC 0:00 运行
  workflow_dispatch: {}
```

---

## 🆘 获取帮助

如遇到问题：
1. 查看 Actions 日志中的错误信息
2. 参考本文档的故障排查部分
3. 检查 README_CN.md 中的详细说明
4. 在 GitHub Issues 提问

---

## ✅ 部署检查清单

- [ ] Notion Integration 已创建并获取 Token
- [ ] 三个 Notion 数据库已创建并按要求添加属性
- [ ] 三个数据库都已授权给 Integration
- [ ] 获取了三个数据库的 ID（32 位，无中划线）
- [ ] GitHub 仓库已创建并推送代码
- [ ] 四个 Secrets 已正确配置
- [ ] GitHub Pages 已启用（Source: GitHub Actions）
- [ ] 笔记 TXT 文件已放入 `notes/` 目录
- [ ] 首次推送后查看 Actions 执行成功
- [ ] Notion 三个数据库中已有数据
- [ ] 访问 Pages URL 可以看到热力图
- [ ] 热力图已嵌入 Notion 数据库或 Dashboard

完成以上步骤后，你的微信读书笔记自动化同步系统就完全部署好了！🎉
