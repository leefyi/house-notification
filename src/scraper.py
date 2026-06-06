import os
import sys
import json
import ssl
import urllib.request
import urllib.parse
from html.parser import HTMLParser
from datetime import datetime, timezone, timedelta

TARGET_URL = "https://zjj.sz.gov.cn/ztfw/zfbz/tzgg2017/"
PAGES_TO_CHECK = 3
KEYWORDS = ["保租房", "公租房", "认租", "保障性租赁住房", "公共租赁住房", "配租"]
BARK_SERVER = "https://api.day.app"
CACHE_FILE = ".cache/seen_urls.json"

CST = timezone(timedelta(hours=8))


class AnnouncementParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.announcements = []
        self._in_list = False
        self._in_li = False
        self._in_a = False
        self._in_span = False
        self._current = {}

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag == "ul" and attrs_dict.get("class") == "ftdt-list":
            self._in_list = True
            return
        if not self._in_list:
            return
        if tag == "li":
            self._in_li = True
            self._current = {}
        elif tag == "a" and self._in_li and "top_" in attrs_dict.get("class", ""):
            self._in_a = True
            self._current["url"] = attrs_dict.get("href", "")
            self._current["title"] = attrs_dict.get("title", "")
        elif tag == "span" and self._in_li:
            self._in_span = True

    def handle_endtag(self, tag):
        if tag == "ul" and self._in_list:
            self._in_list = False
        if tag == "li" and self._in_li:
            self._in_li = False
            if self._current.get("url"):
                self.announcements.append(self._current)
            self._current = {}
        if tag == "a":
            self._in_a = False
        if tag == "span":
            self._in_span = False

    def handle_data(self, data):
        if self._in_span and self._in_li:
            data = data.strip()
            if data:
                self._current["date"] = data


def _ssl_context():
    try:
        import certifi
        ctx = ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        ctx = ssl.create_default_context()
    return ctx


def fetch_page(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "zh-CN,zh;q=0.9",
    })
    with urllib.request.urlopen(req, timeout=30, context=_ssl_context()) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        return resp.read().decode(charset)


def parse_announcements(html):
    parser = AnnouncementParser()
    parser.feed(html)
    return parser.announcements


def filter_by_keywords(announcements):
    matched = []
    for ann in announcements:
        title = ann.get("title", "")
        if any(kw in title for kw in KEYWORDS):
            matched.append(ann)
    return matched


def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    return {"seen_urls": [], "last_check": None}


def save_cache(cache):
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def send_bark(title, body, device_key, url=None):
    payload = {"title": title, "body": body, "device_key": device_key}
    if url:
        payload["url"] = url
    data = json.dumps(payload).encode()
    bark_url = f"{BARK_SERVER}/push"
    req = urllib.request.Request(
        bark_url, data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10, context=_ssl_context()) as resp:
        return json.loads(resp.read().decode())


def _page_url(page_num):
    if page_num <= 1:
        return TARGET_URL
    return TARGET_URL + f"index_{page_num}.html"


def main():
    device_key = os.environ.get("BARK_DEVICE_KEY")
    if not device_key:
        print("Error: BARK_DEVICE_KEY not set")
        sys.exit(1)

    all_announcements = []
    print(f"[{datetime.now(CST).isoformat()}] Fetching announcements...")
    for page in range(1, PAGES_TO_CHECK + 1):
        url = _page_url(page)
        try:
            html = fetch_page(url)
            page_anns = parse_announcements(html)
            all_announcements.extend(page_anns)
            print(f"  Page {page}: {len(page_anns)} items")
        except Exception as e:
            error_msg = f"网站抓取失败 (page {page}): {e}"
            print(error_msg)
            if page == 1:
                send_bark("⚠️ 住房监控异常", error_msg, device_key)
                sys.exit(1)

    print(f"Total: {len(all_announcements)} announcements")

    matched = filter_by_keywords(all_announcements)
    print(f"Matched: {len(matched)} after keyword filter")

    cache = load_cache()
    seen_urls = set(cache.get("seen_urls", []))

    new_announcements = [a for a in matched if a["url"] not in seen_urls]
    print(f"New: {len(new_announcements)}")

    if new_announcements:
        for ann in new_announcements:
            title = "🏠 保租房/公租房新公告"
            body = ann["title"]
            if ann.get("date"):
                body += f"\n{ann['date']}"
            print(f"  -> Sending: {ann['title']}")
            send_bark(title, body, device_key, url=ann["url"])
    else:
        now = datetime.now(CST)
        send_bark(
            "✅ 住房监控正常",
            f"检查完毕，暂无新公告\n{now.strftime('%H:%M')}",
            device_key,
        )
        print("No new announcements, sent confirmation")

    for ann in new_announcements:
        seen_urls.add(ann["url"])

    all_seen = list(seen_urls)
    if len(all_seen) > 500:
        all_seen = all_seen[-500:]

    cache["seen_urls"] = all_seen
    cache["last_check"] = datetime.now(CST).isoformat()
    save_cache(cache)
    print("Cache updated")


if __name__ == "__main__":
    main()
