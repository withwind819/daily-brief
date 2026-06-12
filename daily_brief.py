import os, datetime, time, socket, urllib.request
import yaml, feedparser, requests

UA = "Mozilla/5.0 (compatible; DailyBrief/1.0)"
FEED_TIMEOUT = 12  # 单个源抓取超时(秒)，避免某个慢源拖垮整体

LOOKBACK_HOURS = 24        # 只要最近24小时内的新消息
MAX_PER_FEED   = 8         # 每个源最多取几条
MAX_PER_CAT    = 15        # 每个板块最多展示几条，控制清单长度
MODEL          = "claude-sonnet-4-6"


def load_feeds():
    with open("feeds.yaml", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    out = []
    for cat, items in cfg["categories"].items():
        for it in items:
            out.append((cat, it["name"], it["url"]))
    return out


def fetch_feed(url):
    """带 UA 和超时地抓取并解析单个源。"""
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    data = urllib.request.urlopen(req, timeout=FEED_TIMEOUT).read()
    return feedparser.parse(data)


def is_recent(entry, cutoff):
    t = entry.get("published_parsed") or entry.get("updated_parsed")
    if not t:
        return False  # 拿不到时间的丢弃，保证严格在时间窗口内
    return time.mktime(t) >= cutoff


def collect():
    cutoff = time.time() - LOOKBACK_HOURS * 3600
    blocks = {}
    for cat, name, url in load_feeds():
        try:
            feed = fetch_feed(url)
        except Exception as e:
            print(f"[warn] {name} 抓取失败: {e}")
            continue
        entries = [e for e in feed.entries if is_recent(e, cutoff)][:MAX_PER_FEED]
        for e in entries:
            title = (e.get("title") or "").strip()
            link = e.get("link", "")
            if title:
                blocks.setdefault(cat, []).append({"title": title, "link": link, "src": name})
        print(f"[ok] {name}: {len(entries)} 条")
    for cat in blocks:
        blocks[cat] = blocks[cat][:MAX_PER_CAT]
    return blocks


def summarize(blocks):
    if not blocks:
        return None
    from anthropic import Anthropic
    raw = "\n\n".join(
        f"## {cat}\n" + "\n".join(f"- {i['title']} | 来源:{i['src']} | {i['link']}" for i in items)
        for cat, items in blocks.items())
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"],
                       base_url=os.environ.get("ANTHROPIC_BASE_URL"))
    prompt = f"""你是一名资深科技编辑。下面是今天 AI / 科技 / 创投 三个领域抓取到的新闻条目。
请生成一份简洁的中文早报，要求：
1. 按「AI」「科技」「创投」三个板块组织；
2. 每个板块挑选 3-6 条最重要的，合并重复事件，每条一句话讲清楚「发生了什么 + 为什么重要」；
3. 保留原文链接，用 Markdown 格式 [标题](链接)；
4. 开头加一句今日总览，不超过两句话；
5. 输出纯 Markdown，不要额外说明。

原始素材：
{raw}
"""
    msg = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text


def format_plain(blocks):
    """不调用任何 AI，直接把抓取结果整理成 Markdown 清单。"""
    today = datetime.date.today().strftime("%Y-%m-%d")
    parts = [f"# 每日早报 {today}", f"_最近 {LOOKBACK_HOURS} 小时 · AI / 科技 / 创投_", ""]
    for cat in ("AI", "科技", "创投"):
        items = blocks.get(cat)
        if not items:
            continue
        parts.append(f"## {cat}（{len(items)} 条）")
        for i in items:
            if i["link"]:
                parts.append(f"- [{i['title']}]({i['link']}) — {i['src']}")
            else:
                parts.append(f"- {i['title']} — {i['src']}")
        parts.append("")
    return "\n".join(parts)


def push_wechat(title, markdown):
    key = os.environ["SERVERCHAN_KEY"]
    r = requests.post(
        f"https://sctapi.ftqq.com/{key}.send",
        data={"title": title, "desp": markdown},
        timeout=20,
    )
    print("推送结果:", r.status_code, r.text[:200])


def main():
    blocks = collect()
    if not blocks:
        print("今天没抓到内容，跳过推送")
        return
    # 有 ANTHROPIC_API_KEY 就用 AI 汇总，否则出纯清单（零成本）
    if os.environ.get("ANTHROPIC_API_KEY"):
        report = summarize(blocks)
    else:
        report = format_plain(blocks)
    print("\n===== 早报预览 =====\n")
    print(report)
    if os.environ.get("SERVERCHAN_KEY"):
        today = datetime.date.today().strftime("%m/%d")
        push_wechat(f"每日早报 {today}", report)
    else:
        print("\n[提示] 未设置 SERVERCHAN_KEY，仅本地预览，未推送。")


if __name__ == "__main__":
    main()
