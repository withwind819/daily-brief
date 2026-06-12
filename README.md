# 每日早报看板（AI / 科技 / 创投）

抓取多个 RSS 源 -> 存入 SQLite（按发布日期归档）-> 网页按日期浏览。
支持两种运行方式：本地 Flask，或 GitHub Actions + Pages 全自动云端。

## 目录结构
    feeds.yaml                 信息源配置（AI / 科技 / 创投，可增删）
    backend/fetch.py           抓取脚本：拉取所有源，去重写入 backend/news.db
    backend/export_static.py   把 news.db 导出为 frontend/data/*.json（供 Pages 用）
    backend/server.py          Flask 服务：API + 前端页面（本地用）
    frontend/index.html        前端单页：日期切换 + 分类筛选 + 列表（双模式）
    frontend/data/             静态 JSON（导出后生成；Pages 模式下前端读这里）
    .github/workflows/daily-brief.yml  每天自动抓取 + 部署 Pages

前端是「双模式」：本地有 Flask 时读 /api，部署在 Pages（无后端）时自动读 data/ 下的 JSON。

## 方式一：本地运行
    pip install -r requirements.txt
    python backend/fetch.py            # 抓数据
    python backend/server.py           # 浏览器开 http://127.0.0.1:5000

## 方式二：GitHub Actions + Pages（全自动，电脑关机也能更新）
1. 把本项目推到一个 GitHub 仓库（公开或私有均可；私有需 Pages 支持）。
2. 仓库 Settings -> Pages -> Build and deployment -> Source 选 "GitHub Actions"。
3. 工作流权限：Settings -> Actions -> General -> Workflow permissions
   选 "Read and write permissions"（让 Actions 能把数据提交回仓库）。
4. 进 Actions 页面手动点 Run workflow 跑一次（或直接 push 触发）。
   跑完后访问 Settings -> Pages 顶部给出的网址即可看到看板。
5. 之后每天北京时间 07:00 自动抓取、更新并重新发布，无需开电脑。

说明：工作流每天会运行 fetch.py 抓新内容、export_static.py 导出 JSON，
并把 backend/news.db 与 frontend/data/ 提交回仓库，让历史持续累积。

## 接口（仅本地 Flask 模式）
    GET /api/dates                  有数据的日期列表（倒序，含每天条数）
    GET /api/news?date=YYYY-MM-DD   指定日期的消息（按分类分组）

## 自定义
- 增删信息源：编辑 feeds.yaml
- 保留天数 / 每源条数：改 backend/fetch.py 顶部 KEEP_DAYS、MAX_PER_FEED
- 定时时间：改 .github/workflows/daily-brief.yml 的 cron
