#!/usr/bin/env python3
"""Build Shopify productSet records for the full Aventon e-bike lineup.

Sources: aventon.com's public product JSON (current models, prices, UPCs, photos, copy) and
migration/inventory/locally-aventon.csv (Locally's Aventon catalog: current-season models that
aren't on aventon.com). One Shopify product per model; step-over and step-through frames are
combined where Aventon sells both. The website listing is never sellable online (0 stock, no UPC;
the owner can't collect the $160 assembly and card fees online). Bikes on the floor live on a hidden
"<model> (In-Store Stock)" product whose variants carry the Aventon UPC (how Locally matches them).
The four listings that used to feed Locally are updated in place (variant ids kept, matched by UPC).

Stock: migration/inventory/ebike-stock.json lists the UPCs in the shop; each gets inventory 1 on the
In-Store Stock product. Listings stay at 0 (inventoryPolicy DENY), so nothing can be bought online.

Writes migration/inventory/aventon/<handle>.json = {"identifier", "input", "existing", "stock"}.
Usage: python3 -I scripts/inventory/aventon.py
"""
import csv, html, json, os, re, time, urllib.request

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
INV = os.path.join(ROOT, "migration", "inventory")
OUT = os.path.join(INV, "aventon")
UA = {"User-Agent": "Mozilla/5.0 (compatible; QuestSync/1.0)"}
PHONE = "815.433.2200"
MAX_IMAGES = 15

# handle, title, sources [(aventon handle | "locally:<product name>", frame label)], option order, existing product id,
# value maps (Aventon value -> value already used on the existing product).
FAMILIES = [
    {"handle": "aventon-level-3", "title": "Aventon Level 3", "existing": "gid://shopify/Product/9179283456222",
     "sources": [("level-3-commuter-ebike", "Step Over"), ("level-3-step-through-commuter-ebike", "Step Thru")],
     "options": ["Size", "Style", "Color"], "discontinued": True},
    {"handle": "aventon-level-4", "title": "Aventon Level 4 REC", "existing": "gid://shopify/Product/9189850448094",
     "sources": [("level-4-rec-ebike", "Step Over"), ("level-4-rec-step-through-ebike", "Step-thru")],
     "options": ["Style", "Size", "Color"], "map": {"S/M": "Regular"}},
    {"handle": "aventon-aventure-3", "title": "Aventon Aventure 3", "existing": "gid://shopify/Product/9189855330526",
     "sources": [("aventure-3-ebike", "Step Over"), ("aventure-3-step-through-ebike", "Step-thru")],
     "options": ["Style", "Size", "Color"], "map": {"Cobalt Blue": "Cobalt"}},
    {"handle": "aventon-pace-5-rec", "title": "Aventon Pace 5 REC Step-Through", "sources": [("pace-5-rec-step-through-ebike", None)]},
    {"handle": "aventon-level-4-adv", "title": "Aventon Level 4 ADV",
     "sources": [("level-4-adv-ebike", "Step-Over"), ("level-4-adv-step-through-ebike", "Step-Through")],
     "options": ["Style", "Size", "Color"]},
    {"handle": "aventon-current-exp", "title": "Aventon Current EXP", "sources": [("current-exp-ebike", None)]},
    {"handle": "aventon-current-adv", "title": "Aventon Current ADV", "sources": [("current-adv-ebike", None)]},
    {"handle": "aventon-ramblas-adv", "title": "Aventon Ramblas ADV", "sources": [("ramblas-adv-ebike", None)]},
    {"handle": "aventon-soltera-3-adv", "title": "Aventon Soltera 3 ADV", "sources": [("soltera-3-ebike", None)]},
    {"handle": "aventon-aventure-m", "title": "Aventon Aventure M", "sources": [("aventure-m-ebike", None)]},
    {"handle": "aventon-abound-lr", "title": "Aventon Abound LR", "sources": [("abound-lr-ebike", None)]},
    {"handle": "aventon-abound-sr", "title": "Aventon Abound SR", "sources": [("abound-sr-ebike", None)]},
    {"handle": "aventon-ramblas", "title": "Aventon Ramblas", "sources": [("locally:Ramblas Ebike", None)]},
]
# Owner, 2026-10-24: no longer available and none in stock -> archived, never rebuilt.
REMOVED = ["Pace 4", "Level.2 / Level 2", "Current LTD", "Sinch 2.5", "Soltera 2.5", "Pace 500.3 Step-Through"]
LOCALLY_SEASON = "Fall 26"
LOCALLY_SIZES = {"R": "Regular", "L": "Large", "S": "Small", "M": "Medium", "XL": "Extra Large"}


def get_json(url):
    for i in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception:
            time.sleep(5 * (i + 1))
    raise RuntimeError("fetch failed: " + url)


def aventon_source(handle):
    p = get_json(f"https://www.aventon.com/products/{handle}.json")["product"]
    names = [o["name"] for o in p["options"]]
    variants = []
    for v in p["variants"]:
        opts = dict(zip(names, [v.get("option1"), v.get("option2"), v.get("option3")]))
        variants.append({"upc": v["barcode"], "size": opts.get("Size"), "color": opts.get("Color"),
                         "price": float(v["price"]), "compare": float(v["compare_at_price"] or 0),
                         "available": bool(v.get("available", True))})
    by_variant = {}
    for v in p["variants"]:
        by_variant[v["id"]] = v
    images, seen = [], set()
    for im in p["images"]:
        key = re.sub(r"\?.*", "", im["src"])
        if key in seen:
            continue
        seen.add(key)
        colors = sorted({(dict(zip(names, [by_variant[i].get("option1"), by_variant[i].get("option2"), by_variant[i].get("option3")]))).get("Color")
                         for i in im.get("variant_ids", []) if i in by_variant} - {None})
        images.append({"src": im["src"], "colors": colors})
    return {"body": p["body_html"] or "", "variants": variants, "images": images, "url": f"https://www.aventon.com/products/{handle}"}


def locally_source(name, rows):
    rs = [r for r in rows if r["product_name"] == name and r["product_season"] == LOCALLY_SEASON]
    variants = [{"upc": r["product_upc"], "size": LOCALLY_SIZES.get(r["product_size_1"], r["product_size_1"]),
                 "color": r["product_color_name"], "price": float(r["product_msrp_USD"]), "compare": 0.0, "available": True}
                for r in rs]
    images, seen = [], set()
    for r in rs:
        if r["product_image_url"] and r["product_image_url"] not in seen:
            seen.add(r["product_image_url"])
            images.append({"src": r["product_image_url"], "colors": [r["product_color_name"]]})
    body = f"<p>{html.escape(rs[0]['product_description'])}</p>" if rs else ""
    return {"body": body, "variants": variants, "images": images, "url": rs[0]["product_url"] if rs else ""}


def quest_block(title, discontinued=False):
    order = ("<li>Aventon has discontinued this model: only the bikes we have in stock are available, while they last.</li>"
             if discontinued else
             f"<li>Colors and sizes we don't have in stock can be special ordered. Call {PHONE} or request info below.</li>")
    return ("<h2>Buying your Aventon from Quest Watersports</h2><ul>"
            "<li>Every e-bike purchased through Quest Watersports includes a <strong>$160 assembly and tuning fee</strong>.</li>"
            + order + "<li>Financing is available through Synchrony, subject to credit approval.</li></ul>")


def build(fam, rows, stock):
    parts = []
    for src, frame in fam["sources"]:
        s = locally_source(src[8:], rows) if src.startswith("locally:") else aventon_source(src)
        parts.append((s, frame))
    vmap = fam.get("map", {})
    opt_names = fam.get("options") or (["Size", "Color"] if any(v["size"] for s, _ in parts for v in s["variants"]) else ["Color"])
    variants, values = [], {n: [] for n in opt_names}
    for s, frame in parts:
        for v in s["variants"]:
            vals = {"Style": frame, "Size": vmap.get(v["size"], v["size"]), "Color": vmap.get(v["color"], v["color"])}
            ov = []
            for n in opt_names:
                val = vals[n] or "One Size"
                ov.append({"optionName": n, "name": val})
                if val not in values[n]:
                    values[n].append(val)
            var = {"optionValues": ov, "price": f"{v['price']:.2f}", "barcode": v["upc"], "sku": v["upc"],
                   "inventoryPolicy": "DENY", "inventoryItem": {"tracked": True}, "taxable": True}
            if v["compare"] > v["price"]:
                var["compareAtPrice"] = f"{v['compare']:.2f}"
            variants.append(var)
    imgs, seen = [], set()
    per_part = MAX_IMAGES // len(parts)
    for s, frame in parts:
        for im in s["images"][:per_part]:
            if im["src"] in seen:
                continue
            seen.add(im["src"])
            imgs.append({"originalSource": im["src"], "contentType": "IMAGE",
                         "alt": fam["title"] + (f" {frame}" if frame else "") + (f" in {', '.join(im['colors'])}" if im["colors"] else "") + " e-bike"})
    imgs = imgs[:MAX_IMAGES]
    body = parts[0][0]["body"].strip()
    if len(parts) > 1 and parts[1][0]["body"].strip() and parts[1][0]["body"].strip() != body:
        body += f"<h3>{parts[1][1]} frame</h3>" + parts[1][0]["body"].strip()
    low = min(float(v["price"]) for v in variants)
    stocked = [v["barcode"] for v in variants if v["barcode"] in stock]
    inp = {
        "title": fam["title"], "handle": fam["handle"], "vendor": "Aventon", "productType": "eBike",
        "descriptionHtml": body + quest_block(fam["title"], fam.get("discontinued")),
        "tags": ["inventory", "inventory-ebikes", "inventory-new", "make:Aventon", "type:eBike", "aventon-catalog"]
                + (["in-stock"] if stocked else ["special-order"]) + (["discontinued"] if fam.get("discontinued") else []),
        "status": "ACTIVE", "templateSuffix": "inventory",
        "seo": {"title": f"{fam['title']} Electric Bike | Ottawa, IL Aventon Dealer"[:70],
                "description": (f"{fam['title']} e-bike from ${low:,.0f} at Quest Watersports, your Aventon dealer in Ottawa, IL. "
                                + ("In stock now" if stocked else "Special order") + f" — call {PHONE}. Synchrony financing available.")[:320]},
        "productOptions": [{"name": n, "values": [{"name": x} for x in values[n]]} for n in opt_names],
        "variants": variants,
        "metafields": [
            {"namespace": "custom", "key": "make", "type": "single_line_text_field", "value": "Aventon"},
            {"namespace": "custom", "key": "model", "type": "single_line_text_field", "value": fam["title"].replace("Aventon ", "")},
            {"namespace": "custom", "key": "condition", "type": "single_line_text_field", "value": "New"},
            {"namespace": "custom", "key": "msrp_label", "type": "single_line_text_field", "value": "MSRP"},
            {"namespace": "custom", "key": "assembly_fee", "type": "number_decimal", "value": "160.00"},
            {"namespace": "custom", "key": "special_order", "type": "boolean", "value": "false" if stocked or fam.get("discontinued") else "true"},
            {"namespace": "custom", "key": "call_for_price", "type": "boolean", "value": "false"},
            {"namespace": "custom", "key": "sale_pending", "type": "boolean", "value": "false"},
            {"namespace": "custom", "key": "manufacturer_url", "type": "single_line_text_field", "value": parts[0][0]["url"]},
        ],
        "files": imgs,
    }
    stock_map = {v["barcode"]: (1 if v["barcode"] in stock else 0) for v in variants}
    feed = feed_record(fam, inp, variants, opt_names, stocked)
    # The website listing is never sellable online: no UPCs (so Locally only sees the stock product), 0 stock.
    names = [" / ".join(o["name"] for o in v["optionValues"]) for v in variants if v["barcode"] in stock]
    for v in variants:
        v["sku"] = "W-" + v["barcode"]
        v["barcode"] = None
    inp["metafields"].append({"namespace": "custom", "key": "in_stock_list", "type": "list.single_line_text_field",
                              "value": json.dumps(names)})
    return {"identifier": {"id": fam["existing"]} if fam.get("existing") else {"handle": fam["handle"]},
            "input": inp, "existing": fam.get("existing"), "stock": stock_map, "feed": feed}


def feed_record(fam, inp, variants, opt_names, stocked):
    """Hidden "In-Store Stock" product: the units on the floor, with UPCs, inventory 1 each.
    Published ONLY to the Locally Sales Channel and Point of Sale, never the Online Store."""
    if not stocked:
        return None
    vs = [dict(v, optionValues=list(v["optionValues"])) for v in variants if v["barcode"] in stocked]
    used = {n: [] for n in opt_names}
    for v in vs:
        for o in v["optionValues"]:
            if o["name"] not in used[o["optionName"]]:
                used[o["optionName"]].append(o["name"])
    return {"identifier": {"handle": fam["handle"] + "-in-store-stock"},
            "input": {"title": fam["title"] + " (In-Store Stock)", "handle": fam["handle"] + "-in-store-stock",
                      "vendor": "Aventon", "productType": "eBike", "status": "ACTIVE",
                      "descriptionHtml": f"<p>Floor stock at Quest Watersports. Website listing: /products/{fam['handle']}</p>",
                      "tags": ["locally-feed", "in-store-stock", "make:Aventon", "type:eBike"],
                      "productOptions": [{"name": n, "values": [{"name": x} for x in used[n]]} for n in opt_names],
                      "variants": vs, "files": inp["files"][:1]},
            "stock": {v["barcode"]: 1 for v in vs}}


def main():
    rows = list(csv.DictReader(open(os.path.join(INV, "locally-aventon.csv"), encoding="utf-8")))
    stock = json.load(open(os.path.join(INV, "ebike-stock.json")))["in_stock"]
    os.makedirs(OUT, exist_ok=True)
    seen_upcs = set()
    for fam in FAMILIES:
        rec = build(fam, rows, stock)
        seen_upcs |= set(rec["stock"])
        json.dump(rec, open(os.path.join(OUT, fam["handle"] + ".json"), "w"), indent=1, ensure_ascii=False)
        if rec["feed"]:
            json.dump(rec["feed"], open(os.path.join(OUT, fam["handle"] + "-in-store-stock.json"), "w"), indent=1, ensure_ascii=False)
        n_in = sum(rec["stock"].values())
        print(f"{fam['handle']:34} variants {len(rec['input']['variants']):2}  images {len(rec['input']['files']):2}  in stock {n_in}")
        time.sleep(0.5)
    missing = set(stock) - seen_upcs
    if missing:
        print("STOCK UPCs NOT IN ANY MODEL:", sorted(missing))


if __name__ == "__main__":
    main()
