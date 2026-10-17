#!/usr/bin/env python3
"""Diff a fresh crawl dir against migration/source and emit a JSON report.

Usage: python3 -I scripts/sync/diff.py FRESH_DIR [--old DIR] [--report PATH]
"""
import argparse, difflib, glob, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
MAX_DIFF = 4000

NOISE = [
    re.compile(r"Google Tag Manager", re.I),
    re.compile(r"^\s*(©|copyright)\b", re.I),
    re.compile(r"\b\d[\d,]*\s*(results?|items?|units?|vehicles?|boats?|listings?|products?)\s+(found|available|in stock)\b", re.I),
    re.compile(r"\b(showing|displaying)\s+\d+\s*[-–to]+\s*\d+\s+of\s+\d+", re.I),
    re.compile(r"\bpage\s+\d+\s+of\s+\d+\b", re.I),
]
YEAR = re.compile(r"\b(19|20)\d\d\b")


def normalize(text):
    out = []
    for line in text.splitlines():
        line = re.sub(r"\s+", " ", line).strip()
        if not line or any(p.search(line) for p in NOISE):
            continue
        out.append(line)
    return out


def mapping():
    """slug -> target string."""
    m = {"home": "home"}
    # fallback: docs/SITE-SPEC.md table
    spec = os.path.join(REPO, "docs", "SITE-SPEC.md")
    if os.path.exists(spec):
        for l in open(spec, encoding="utf-8"):
            c = [x.strip() for x in l.split("|")]
            if len(c) > 5 and c[1].startswith("`") and c[3] and not c[3].startswith("WP"):
                handle = c[1].strip("`")
                for s in re.split(r",\s*", c[3]):
                    s = s.strip()
                    if s and "(" not in s:
                        m.setdefault(s, f"page:{handle}")
    for p in glob.glob(os.path.join(REPO, "migration", "pages", "*.json")):
        try:
            d = json.load(open(p, encoding="utf-8"))
        except Exception:
            continue
        h = d.get("handle") or os.path.basename(p)[:-5]
        for s in d.get("source_slugs", []):
            m[s] = f"page:{h}"
    for p in glob.glob(os.path.join(REPO, "migration", "articles", "*.json")):
        h = os.path.basename(p)[:-5]
        m["news__" + h] = f"article:{h}"
    return m


def images(text):
    return set(re.findall(r"!\[[^\]]*\]\(([^)\s]+)\)", text))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("fresh")
    ap.add_argument("--old", default=os.path.join(REPO, "migration", "source"))
    ap.add_argument("--report", default=os.path.join(HERE, "last-report.json"))
    a = ap.parse_args()

    tmap = mapping()
    meta_p = os.path.join(a.fresh, "crawl-meta.json")
    meta = json.load(open(meta_p)) if os.path.exists(meta_p) else {}
    report = {"changed": [], "new_urls": meta.get("new_urls", []), "removed_urls": meta.get("removed_urls", []),
              "new_images": [], "failed": meta.get("failed", []), "partial": meta.get("partial", False)}
    seen_imgs = set()
    for f in sorted(glob.glob(os.path.join(a.fresh, "*.md"))):
        slug = os.path.basename(f)[:-3]
        new_t = open(f, encoding="utf-8").read()
        op = os.path.join(a.old, slug + ".md")
        old_t = open(op, encoding="utf-8").read() if os.path.exists(op) else ""
        if not os.path.exists(op):
            continue  # brand-new page: reported via new_urls
        o, n = normalize(old_t), normalize(new_t)
        if o == n:
            continue
        ud = "\n".join(difflib.unified_diff(o, n, "old/" + slug, "new/" + slug, lineterm="", n=1))
        if len(ud) > MAX_DIFF:
            ud = ud[:MAX_DIFF] + "\n...[truncated]"
        report["changed"].append({"slug": slug, "shopify_target": tmap.get(slug, "unmapped"), "unified_diff": ud})
        for im in sorted(images(new_t) - images(old_t)):
            if im not in seen_imgs:
                seen_imgs.add(im)
                report["new_images"].append({"slug": slug, "url": im})
    report["summary"] = {"changed": len(report["changed"]), "new_urls": len(report["new_urls"]),
                         "removed_urls": len(report["removed_urls"]), "failed": len(report["failed"])}
    s = json.dumps(report, indent=1, ensure_ascii=False)
    with open(a.report, "w", encoding="utf-8") as fh:
        fh.write(s + "\n")
    print(s)
    return 0


if __name__ == "__main__":
    sys.exit(main())
