#!/usr/bin/env python3
"""把 news.db 导出为静态 JSON，供 GitHub Pages 等静态托管使用。
输出：
  frontend/data/index.json        [{date, count}, ...] 倒序
  frontend/data/<YYYY-MM-DD>.json  {date, total, categories:{分类:[...]}}
前端在没有后端 API 时会自动改读这些文件。
"""
import os, json, sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DB = os.path.join(HERE, "news.db")
OUT = os.path.join(ROOT, "frontend", "data")
CAT_ORDER = ["AI", "科技", "创投"]


def main():
    os.makedirs(OUT, exist_ok=True)
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row

    dates = con.execute(
        "SELECT date, COUNT(*) c FROM news GROUP BY date ORDER BY date DESC"
    ).fetchall()
    index = [{"date": r["date"], "count": r["c"]} for r in dates]
    with open(os.path.join(OUT, "index.json"), "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=0)

    for r in dates:
        date = r["date"]
        rows = con.execute(
            "SELECT category, source, title, link, summary, published "
            "FROM news WHERE date=? ORDER BY published DESC", (date,)
        ).fetchall()
        grouped = {}
        for x in rows:
            grouped.setdefault(x["category"], []).append({
                "source": x["source"], "title": x["title"], "link": x["link"],
                "summary": x["summary"], "published": x["published"],
            })
        ordered = {c: grouped[c] for c in CAT_ORDER if c in grouped}
        for c in grouped:
            ordered.setdefault(c, grouped[c])
        payload = {"date": date, "total": len(rows), "categories": ordered}
        with open(os.path.join(OUT, f"{date}.json"), "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=0)

    con.close()
    print(f"导出完成：{len(index)} 个日期 -> {OUT}")


if __name__ == "__main__":
    main()
