#!/usr/bin/env python3
"""每日早报 API + 前端静态服务。
端点：
  GET /                      前端页面
  GET /api/dates             有数据的日期列表（倒序）
  GET /api/news?date=YYYY-MM-DD   当天消息，按分类分组
"""
import os, sqlite3
from flask import Flask, jsonify, request, send_from_directory

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DB = os.path.join(HERE, "news.db")
FRONTEND = os.path.join(ROOT, "frontend")

CAT_ORDER = ["AI", "科技", "创投"]

app = Flask(__name__, static_folder=None)


def query(sql, args=()):
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    rows = con.execute(sql, args).fetchall()
    con.close()
    return rows


@app.route("/")
def index():
    return send_from_directory(FRONTEND, "index.html")


@app.route("/api/dates")
def api_dates():
    rows = query("SELECT date, COUNT(*) c FROM news GROUP BY date ORDER BY date DESC")
    return jsonify([{"date": r["date"], "count": r["c"]} for r in rows])


@app.route("/api/news")
def api_news():
    date = request.args.get("date")
    if not date:
        # 默认最新一天
        r = query("SELECT date FROM news ORDER BY date DESC LIMIT 1")
        if not r:
            return jsonify({"date": None, "categories": {}})
        date = r[0]["date"]
    rows = query(
        "SELECT category, source, title, link, summary, published "
        "FROM news WHERE date=? ORDER BY published DESC",
        (date,),
    )
    grouped = {}
    for r in rows:
        grouped.setdefault(r["category"], []).append({
            "source": r["source"], "title": r["title"], "link": r["link"],
            "summary": r["summary"], "published": r["published"],
        })
    # 按固定顺序输出
    ordered = {c: grouped[c] for c in CAT_ORDER if c in grouped}
    for c in grouped:
        if c not in ordered:
            ordered[c] = grouped[c]
    return jsonify({"date": date, "categories": ordered,
                    "total": sum(len(v) for v in ordered.values())})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
