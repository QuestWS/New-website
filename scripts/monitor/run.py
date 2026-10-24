#!/usr/bin/env python3
"""Head-to-head site monitor: legacy questwatersports.com vs the new Shopify site.

For each page pair in pairs.json it runs a mobile Lighthouse audit (performance, SEO,
accessibility, best practices, LCP, CLS, TBT, page weight) and on-page SEO checks (title,
meta description, H1s, canonical, structured data, word count, image alt coverage) on both
sites, then appends one row per page per site to monitoring/scores.csv.

Usage: python3 -I scripts/monitor/run.py [--only "Home,Contact"] [--no-lighthouse]
Needs Node (npx lighthouse@12) and the preinstalled Chromium.
"""
import csv, datetime, glob, json, os, re, subprocess, sys, tempfile, urllib.request
from html.parser import HTMLParser

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
CFG = json.load(open(os.path.join(os.path.dirname(__file__), "pairs.json")))
OUT = os.path.join(ROOT, "monitoring", "scores.csv")
FIELDS = ["date", "page", "site", "url", "performance", "seo", "accessibility", "best_practices",
          "lcp_s", "cls", "tbt_ms", "page_kb", "title_len", "meta_desc_len", "h1_count", "canonical",
          "schema_types", "word_count", "img_total", "img_missing_alt", "status"]
UA = {"User-Agent": "Mozilla/5.0 (compatible; QuestMonitor/1.0)"}


def chrome():
    hits = sorted(glob.glob("/opt/pw-browsers/chromium-*/chrome-linux/chrome"))
    return os.environ.get("CHROME_PATH") or (hits[-1] if hits else "")


def url_for(site, path):
    base = CFG["legacy_base"] if site == "legacy" else CFG["new_base"]
    q = "" if site == "legacy" else CFG.get("new_query", "")
    return base + path + (("&" if "?" in path else "?") + q if q else "")


class Page(HTMLParser):
    def __init__(self):
        super().__init__(); self.title = ""; self.in_title = False; self.desc = None; self.h1 = 0
        self.canonical = ""; self.schema = []; self.in_ld = False; self.ld = ""; self.text = []
        self.skip = 0; self.imgs = 0; self.noalt = 0

    def handle_starttag(self, tag, a):
        a = dict(a)
        if tag == "title": self.in_title = True
        elif tag == "meta" and (a.get("name") or "").lower() == "description": self.desc = a.get("content") or ""
        elif tag == "link" and (a.get("rel") or "").lower() == "canonical": self.canonical = a.get("href") or ""
        elif tag == "h1": self.h1 += 1
        elif tag == "script" and (a.get("type") or "") == "application/ld+json": self.in_ld = True; self.ld = ""
        elif tag in ("script", "style", "noscript"): self.skip += 1
        elif tag == "img":
            self.imgs += 1
            if not (a.get("alt") or "").strip(): self.noalt += 1

    def handle_endtag(self, tag):
        if tag == "title": self.in_title = False
        elif tag == "script" and self.in_ld:
            self.in_ld = False
            self.schema += re.findall(r'"@type"\s*:\s*"([^"]+)"', self.ld)
        elif tag in ("script", "style", "noscript") and self.skip: self.skip -= 1

    def handle_data(self, d):
        if self.in_title: self.title += d
        elif self.in_ld: self.ld += d
        elif not self.skip: self.text.append(d)


def onpage(url):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
            status, body = r.status, r.read().decode("utf-8", "replace")
    except Exception as e:
        return {"status": f"error: {e}"[:80]}
    p = Page(); p.feed(body)
    return {"status": status, "title_len": len(p.title.strip()), "meta_desc_len": len(p.desc or ""), "h1_count": p.h1,
            "canonical": "yes" if p.canonical else "no", "schema_types": "|".join(sorted(set(p.schema))),
            "word_count": len(" ".join(p.text).split()), "img_total": p.imgs, "img_missing_alt": p.noalt}


def lighthouse(url):
    with tempfile.TemporaryDirectory() as d:
        out = os.path.join(d, "lh.json")
        cmd = ["npx", "-y", "lighthouse@12", url, "--quiet", "--output=json", f"--output-path={out}",
               "--form-factor=mobile", "--only-categories=performance,seo,accessibility,best-practices",
               "--chrome-flags=--headless=new --no-sandbox"]
        env = dict(os.environ, CHROME_PATH=chrome())
        try:
            subprocess.run(cmd, env=env, timeout=240, capture_output=True)
            j = json.load(open(out))
        except Exception:
            return {}
    c, a = j["categories"], j["audits"]
    sc = lambda k: round((c[k]["score"] or 0) * 100)
    return {"performance": sc("performance"), "seo": sc("seo"), "accessibility": sc("accessibility"),
            "best_practices": sc("best-practices"),
            "lcp_s": round(a["largest-contentful-paint"]["numericValue"] / 1000, 2),
            "cls": round(a["cumulative-layout-shift"]["numericValue"], 3),
            "tbt_ms": round(a["total-blocking-time"]["numericValue"]),
            "page_kb": round(a["total-byte-weight"]["numericValue"] / 1024)}


def main():
    args = sys.argv[1:]
    only = set(args[args.index("--only") + 1].split(",")) if "--only" in args else None
    do_lh = "--no-lighthouse" not in args
    today = datetime.date.today().isoformat()
    rows = []
    for pair in CFG["pairs"]:
        if only and pair["page"] not in only:
            continue
        for site in ("legacy", "new"):
            url = url_for(site, pair[site])
            row = {"date": today, "page": pair["page"], "site": site, "url": CFG["legacy_base" if site == "legacy" else "new_base"] + pair[site]}
            row.update(onpage(url))
            if do_lh:
                row.update(lighthouse(url))
            rows.append(row)
            print(site, pair["page"], {k: row.get(k) for k in ("performance", "seo", "lcp_s", "status")}, flush=True)
    new_file = not os.path.exists(OUT)
    with open(OUT, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        if new_file:
            w.writeheader()
        w.writerows(rows)
    print(f"appended {len(rows)} rows to monitoring/scores.csv")


if __name__ == "__main__":
    main()
