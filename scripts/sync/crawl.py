#!/usr/bin/env python3
"""Crawl the old WordPress site and write text snapshots.

Usage: python3 -I scripts/sync/crawl.py [--out DIR] [--limit N] [--only slug,slug]
Writes DIR/<slug>.md for each fetched page, DIR/urls.txt (full core URL list from the
sitemaps, regardless of --limit) and DIR/crawl-meta.json (new/removed/failed URLs).
"""
import argparse, json, os, re, sys, time, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from extract import html_to_md  # noqa: E402

REPO = os.path.dirname(os.path.dirname(HERE))
BASE = "https://www.questwatersports.com"
UA = "Mozilla/5.0 (compatible; QuestSync/1.0)"
SITEMAPS = [BASE + "/sitemap.xml", BASE + "/wp-sitemap-posts-post-1.xml"]
LEGACY = re.compile(r"-c-\d+/?$")
_last = [0.0]


def fetch(url, retries=3):
    for attempt in range(retries + 1):
        wait = 1.0 - (time.time() - _last[0])
        if wait > 0:
            time.sleep(wait)
        _last[0] = time.time()
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=40) as r:
                return r.read().decode("utf-8", errors="ignore")
        except urllib.error.HTTPError as e:
            if e.code in (403, 429) or e.code >= 500:
                if attempt < retries:
                    time.sleep(5 * 3 ** attempt)
                    continue
            raise
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            if attempt < retries:
                time.sleep(5 * 3 ** attempt)
                continue
            raise


def slug_of(url):
    path = re.sub(r"^https?://[^/]+", "", url).split("?")[0].strip("/")
    return path.replace("/", "__") if path else "home"


def norm_url(u):
    u = u.strip()
    return BASE if u.rstrip("/") == BASE else u


def sitemap_urls():
    urls = []
    for sm in SITEMAPS:
        try:
            xml = fetch(sm)
        except Exception as e:
            print(f"WARN sitemap {sm}: {e}", file=sys.stderr)
            continue
        for u in re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", xml):
            u = norm_url(u)
            if not u.startswith(BASE) or LEGACY.search(u) or u.endswith(".xml"):
                continue
            if u not in urls:
                urls.append(u)
    return urls


def read_urls(path):
    if not os.path.exists(path):
        return []
    return [norm_url(l) for l in open(path, encoding="utf-8") if l.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(REPO, "migration", "source"))
    ap.add_argument("--limit", type=int, default=0, help="only fetch first N pages (testing)")
    ap.add_argument("--only", default="", help="comma-separated slugs to fetch")
    ap.add_argument("--urls-file", default=os.path.join(REPO, "migration", "source-urls.txt"))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    urls = sitemap_urls()
    if not urls:
        print("ERROR: no URLs from sitemaps (blocked?)", file=sys.stderr)
        json.dump({"error": "no sitemap urls"}, open(os.path.join(a.out, "crawl-meta.json"), "w"))
        return 1
    old = read_urls(a.urls_file)
    new_urls = [u for u in urls if u not in old]
    removed = [u for u in old if u not in urls]

    todo = urls
    if a.only:
        want = set(a.only.split(","))
        todo = [u for u in urls if slug_of(u) in want]
    if a.limit:
        todo = todo[: a.limit]
    failed = []
    for i, u in enumerate(todo, 1):
        s = slug_of(u)
        try:
            md = html_to_md(fetch(u))
            with open(os.path.join(a.out, s + ".md"), "w", encoding="utf-8") as f:
                f.write(md)
            print(f"[{i}/{len(todo)}] ok {s}", file=sys.stderr)
        except Exception as e:
            failed.append({"url": u, "error": str(e)})
            print(f"[{i}/{len(todo)}] FAIL {s}: {e}", file=sys.stderr)
    with open(os.path.join(a.out, "urls.txt"), "w") as f:
        f.write("\n".join(urls) + "\n")
    meta = {"fetched": [slug_of(u) for u in todo if slug_of(u) not in {slug_of(x["url"]) for x in failed}],
            "failed": failed, "new_urls": new_urls, "removed_urls": removed,
            "partial": bool(a.limit or a.only)}
    json.dump(meta, open(os.path.join(a.out, "crawl-meta.json"), "w"), indent=1)
    print(f"crawled {len(meta['fetched'])} pages, {len(failed)} failed, {len(new_urls)} new urls, {len(removed)} removed urls", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
