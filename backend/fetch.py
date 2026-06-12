#!/usr/bin/env python3
"""抓取所有 RSS 源，按每条新闻的真实发布日期归档，去重写入 SQLite。
每天运行一次即可；一次运行会把最近若干天的内容都填进库（按各条目的发布日期分桶）。
"""
import os, re, html, time, sqlite3, hashlib, datetime, urllib.request
import yaml, feedparser

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DB = os.path.join(HERE, "news.db")
FEEDS = os.path.join(ROOT, "feeds.yaml")

UA = "Mozilla/5.0 (compatible; DailyBrief/1.0)"
FEED_TIMEOUT = 12        # 单源抓取超时(秒)
MAX_PER_FEED = 40        # 每源最多取多少条
KEEP_DAYS = 14           # 只保留最近多少天发布的条目


def clean(t):
    t = re.sub(r"<[^>]+>", "", t or "")
    t = html.unescape(t).strip()
    t = re.sub(r"\s+", " ", t)
    return t


def load_feeds():
    with open(FEEDS, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    out = []
    for cat, items in cfg["categories"].items():
        for it in items:
            out.append((cat, it["name"], it["url"]))
    return out


def fetch_feed(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    data = urllib.request.urlopen(req, timeout=FEED_TIMEOUT).read()
    return feedparser.parse(data)


def init_db():
    con = sqlite3.connect(DB)
    con.execute("""CREATE TABLE IF NOT EXISTS news(
        id TEXT PRIMARY KEY,
        date TEXT NOT NULL,
        published REAL,
        category TEXT,
        source TEXT,
        title TEXT,
        link TEXT,
        summary TEXT
    )""")
    con.execute("CREATE INDEX IF NOT EXISTS idx_date ON news(date)")
    con.commit()
    return con


def main():
    con = init_db()
    cutoff = time.time() - KEEP_DAYS * 86400
    feeds = load_feeds()
    added = 0
    for cat, name, url in feeds:
        try:
            feed = fetch_feed(url)
        except Exception as e:
            print(f"[warn] {name} 抓取失败: {type(e).__name__}")
            continue
        n = 0
        for e in feed.entries[:MAX_PER_FEED]:
            t = e.get("published_parsed") or e.get("updated_parsed")
            if not t:
                continue                      # 无发布时间的丢弃，保证按日期归档准确
            ts = time.mktime(t)
            if ts < cutoff:
                continue
            link = e.get("link", "")
            title = clean(e.get("title", ""))
            if not title or not link:
                continue
            uid = hashlib.sha1(link.encode("utf-8")).hexdigest()
            date = time.strftime("%Y-%m-%d", t)
            summary = clean(e.get("summary", "") or e.get("description", ""))
            if len(summary) > 240:
                summary = summary[:240] + "…"
            try:
                con.execute(
                    "INSERT OR IGNORE INTO news VALUES (?,?,?,?,?,?,?,?)",
                    (uid, date, ts, cat, name, title, link, summary),
                )
                if con.total_changes:
                    n += 1
            except sqlite3.Error as err:
                print(f"[warn] 写入失败: {err}")
        added += n
        print(f"[ok] {name}: 新增 {n} 条")
    # 清理超过保留期的旧数据
    old = (datetime.date.today() - datetime.timedelta(days=KEEP_DAYS)).isoformat()
    con.execute("DELETE FROM news WHERE date < ?", (old,))
    con.commit()
    total = con.execute("SELECT COUNT(*) FROM news").fetchone()[0]
    days = con.execute("SELECT COUNT(DISTINCT date) FROM news").fetchone()[0]
    con.close()
    print(f"\n本次新增 {added} 条；库内共 {total} 条，覆盖 {days} 天。")


if __name__ == "__main__":
    main()
