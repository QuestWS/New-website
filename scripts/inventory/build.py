#!/usr/bin/env python3
"""Turn questwatersports.com inventory into Shopify `productSet` inputs.

Fetches the dealer inventory feed (isapi_xml.php) and, for each AVAILABLE unit, its
photo gallery, then writes one JSON file per unit to migration/inventory/<id>.json:
  {"identifier": {"handle": ...}, "input": <ProductSetInput>, "source": {...}}
Units are never purchasable online: the single variant tracks inventory with 0 on hand
and inventoryPolicy DENY; the theme's product.inventory template shows "Call / Request info".
Also writes migration/inventory/_index.json (all feed ids with status) so the daily sync can
archive units that sold.

Usage: python3 -I scripts/inventory/build.py [--no-images] [--only ID,ID]
"""
import html, json, os, re, sys, time, urllib.request

BASE = "https://www.questwatersports.com"
FEED = BASE + "/isapi_xml.php?result=json&module=inventory&main=&limit=999&orderby=make,model&offset=0"
DETAIL = BASE + "/isapi_xml.php?module=detailed&action=getPage&vid={id}"
OUT = os.path.join(os.path.dirname(__file__), "..", "..", "migration", "inventory")
UA = {"User-Agent": "Mozilla/5.0 (compatible; QuestSync/1.0)"}

# old-site category id -> (product type, collection tag)
CATEGORIES = {
    "22": ("Boat", "inventory-boats"), "28": ("Boat", "inventory-boats"), "45": ("Pontoon", "inventory-boats"),
    "53": ("Boat", "inventory-boats"), "76": ("Fishing Boat", "inventory-boats"), "59": ("Personal Watercraft", "inventory-boats"),
    "78": ("Boat Lift", "inventory-boats"),
    "63": ("Kayak", "inventory-paddlesports"), "64": ("Paddleboard", "inventory-paddlesports"), "69": ("Paddleboard", "inventory-paddlesports"),
    "71": ("Sailboat", "inventory-sailboats"),
    "74": ("eBike", "inventory-ebikes"), "75": ("eBike", "inventory-ebikes"),
}


def get(url, tries=4):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return r.read().decode("utf-8", "replace")
        except Exception:
            time.sleep(5 * (i + 1))
    raise RuntimeError("fetch failed: " + url)


def money(v):
    m = re.sub(r"[^0-9.]", "", str(v or ""))
    return float(m) if m else 0.0


def clean_html(s):
    s = (s or "").replace("\r", "")
    s = re.sub(r"(?is)<(script|style|iframe)[^>]*>.*?</\1>", "", s)
    s = re.sub(r'\s(style|class|align|width|height)="[^"]*"', "", s)
    s = re.sub(r"(<br\s*/?>\s*){2,}", "</p><p>", s)
    s = s.strip()
    return f"<p>{s}</p>" if s and not re.match(r"(?i)<(p|h[1-6]|ul|ol|div|table)\b", s) else s


def slugify(t):
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", t.lower())).strip("-")


def gallery(vid):
    page = get(DETAIL.format(id=vid))
    urls, seen = [], set()
    for m in re.finditer(r"imagetag/%s/([^/\"'\\ ]+)/[sfml]/([^\"'\\ )]+?\.(?:jpe?g|png|webp))" % vid, page, re.I):
        slot, name = m.group(1), m.group(2)
        if slot in seen:
            continue
        seen.add(slot)
        urls.append((0 if slot == "main" else int(slot) if slot.isdigit() else 999, f"{BASE}/imagetag/{vid}/{slot}/l/{name}"))
    return [u for _, u in sorted(urls)]


def build(x, images=True):
    vid = x["id"]
    year = x["year"] if x["year"] not in ("0", "", None) else ""
    model = re.sub(r"^\s*Used\s+", "", x["model"] or "").strip()
    make = (x["make"] or "").strip()
    make_disp = make.title() if make.isupper() and len(make) > 3 else make
    title = " ".join(p for p in [year, make_disp, model] if p)
    used = x["type"] == "Used"
    ptype, ctag = CATEGORIES.get(x["cid"], ("Other", "inventory-other"))
    price, sale = money(x["price"]), money(x["lower_price"])
    call = not price and not sale or "call" in (x["lower_price"] or "").lower()
    now = sale if sale and (not price or sale < price) else price
    variant = {
        "optionValues": [{"optionName": "Title", "name": "Default Title"}],
        "price": f"{now:.2f}",
        "sku": x["stockno"] or f"QW-{vid}",
        "inventoryPolicy": "DENY",
        "inventoryItem": {"tracked": True},
        "taxable": True,
    }
    if sale and price and sale < price:
        variant["compareAtPrice"] = f"{price:.2f}"
    length = ""
    if money(x["length_feet"]):
        length = f"{int(money(x['length_feet']))}'" + (f" {int(money(x['length_inches']))}\"" if money(x["length_inches"]) else "")
    specs = {
        "condition": "Pre-Owned" if used else "New", "year": year, "make": make_disp, "model": model,
        "stock_number": x["stockno"], "length": length, "engine": x["engine"], "horsepower": x["horsepower"],
        "hull_type": x["hull_type"], "fuel_type": x["fuel_type"], "color": x["ext_color"] or x["basic_ext_color"],
    }
    mf = [{"namespace": "custom", "key": k, "type": "single_line_text_field", "value": str(v)} for k, v in specs.items() if v not in ("", None, "0", "-1")]
    mf += [
        {"namespace": "custom", "key": "inventory_id", "type": "single_line_text_field", "value": vid},
        {"namespace": "custom", "key": "call_for_price", "type": "boolean", "value": "true" if call else "false"},
        {"namespace": "custom", "key": "sale_pending", "type": "boolean", "value": "true" if x["pending_sale"] == "1" else "false"},
    ]
    if x.get("YouTube_url"):
        mf.append({"namespace": "custom", "key": "youtube_url", "type": "single_line_text_field", "value": x["YouTube_url"]})
    body = "".join(clean_html(x.get(k)) for k in ("intro_text", "main_text_1", "main_text_2", "main_text_3", "features") if (x.get(k) or "").strip())
    cond = "Pre-Owned" if used else "New"
    seo_title = f"{'Used ' if used else 'New '}{title} for Sale | Ottawa, IL"[:70]
    seo_desc = (f"{cond} {title} for sale at Quest Watersports in Ottawa, IL"
                + (f" — {'call for price' if call else '$' + format(now, ',.0f')}" ) + ". Stock #" + (x["stockno"] or vid)
                + ". Call 815.433.2200 or request info online.")[:320]
    tags = ["inventory", ctag, "inventory-new" if not used else "inventory-pre-owned", f"make:{make_disp}", f"type:{ptype}"]
    if year:
        tags.append(f"year:{year}")
    if x["pending_sale"] == "1":
        tags.append("sale-pending")
    inp = {
        "title": title, "handle": f"{slugify(title)}-{vid}", "descriptionHtml": body or f"<p>{cond} {title}. Call 815.433.2200 for details.</p>",
        "vendor": make_disp or "Quest Watersports", "productType": ptype, "tags": tags, "status": "ACTIVE",
        "templateSuffix": "inventory", "seo": {"title": seo_title, "description": seo_desc},
        "productOptions": [{"name": "Title", "values": [{"name": "Default Title"}]}],
        "variants": [variant], "metafields": mf,
    }
    if images:
        imgs = gallery(vid)
        inp["files"] = [{"originalSource": u, "contentType": "IMAGE", "alt": f"{cond} {title}" + (f" photo {i + 1}" if i else "")} for i, u in enumerate(imgs[:20])]
    return {"identifier": {"handle": inp["handle"]}, "input": inp,
            "source": {"id": vid, "url": BASE + x["url_link"], "when_modified": x["when_modified"], "sold": x["sold"]}}


def main():
    args = sys.argv[1:]
    images = "--no-images" not in args
    only = set(args[args.index("--only") + 1].split(",")) if "--only" in args else None
    os.makedirs(OUT, exist_ok=True)
    feed = json.loads(get(FEED))
    index = {x["id"]: {"sold": x["sold"], "url": BASE + x["url_link"], "when_modified": x["when_modified"]} for x in feed}
    json.dump(index, open(os.path.join(OUT, "_index.json"), "w"), indent=1, sort_keys=True)
    avail = [x for x in feed if x["sold"] == "Available" and x.get("no_display") != "1" and (not only or x["id"] in only)]
    for x in avail:
        rec = build(x, images)
        json.dump(rec, open(os.path.join(OUT, f"{x['id']}.json"), "w"), indent=1, ensure_ascii=False)
        if images:
            time.sleep(0.6)
    print(f"available: {len(avail)}  feed total: {len(feed)}")


if __name__ == "__main__":
    main()
