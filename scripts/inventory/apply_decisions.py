#!/usr/bin/env python3
"""Apply the owner's kayak decisions to the built inventory records.

Reads migration/inventory/<id>.json (from build.py) and migration/inventory/kayak-decisions.json,
and writes the productSet records that should exist in Shopify to migration/inventory/final/<key>.json.
Non-kayak listings pass through unchanged. Kayak/paddleboard listings are written only when the
owner approved them (approved / overrides / to_2027); excluded and held ones are skipped, and new
undecided ones are listed in final/_report.json under "pending" for the owner.

Hobie MAP rules applied (2027 Hobie Kayak Program): 2026/2027 first-quality units at exactly
2027 MSRP; 2025-and-older first-quality units show the 2027 MSRP beside the price (custom.msrp_label)
and may be at most 20% below it — units priced lower are reported under "map_warnings", not changed.

Usage: python3 -I scripts/inventory/apply_decisions.py
"""
import copy, glob, json, os, re

INV = os.path.join(os.path.dirname(__file__), "..", "..", "migration", "inventory")
OUT = os.path.join(INV, "final")
KAYAK_TYPES = ("Kayak", "Paddleboard")
PHONE = "815.433.2200"


# Hobie MAP: no "sale", "clearance" or savings claims in Hobie listings (old-site copy has some).
MAP_SCRUB = [
    r"Save Big on our [^<!]*Clearance!\s*(</strong>|</span>)*\s*(<br\s*/?>)?",
    r"Take advantage of our special pricing on [^.<]+\.\s*Priced at \$[\d,]+, you save \$[\d,]+ off the \d{4} MSRP of \$[\d,]+\.\s*",
    r",? offering a unique opportunity to save almost <strong>\$[\d,]+</strong>",
]


def map_scrub(inp):
    if "make:Hobie" in inp["tags"]:
        for pat in MAP_SCRUB:
            inp["descriptionHtml"] = re.sub(pat, "", inp["descriptionHtml"])


def slugify(t):
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", t.lower())).strip("-")


def set_mf(inp, key, value, typ="single_line_text_field"):
    inp["metafields"] = [m for m in inp["metafields"] if m["key"] != key]
    if value not in (None, ""):
        inp["metafields"].append({"namespace": "custom", "key": key, "type": typ, "value": str(value)})


def mf(inp, key):
    return next((m["value"] for m in inp["metafields"] if m["key"] == key), None)


def set_tags(inp, add=(), remove=()):
    tags = [t for t in inp["tags"] if t not in remove and not any(t.startswith(r[:-1]) for r in remove if r.endswith("*"))]
    inp["tags"] = tags + [t for t in add if t not in tags]


def seo(inp, kind):
    title, price = inp["title"], float(inp["variants"][0]["price"])
    call = mf(inp, "call_for_price") == "true"
    if kind == "special":
        inp["seo"] = {"title": f"{title} | Order in Ottawa, IL"[:70],
                      "description": f"Order the {title} from Quest Watersports, your Hobie dealer in Ottawa, IL. "
                                     f"${price:,.0f} MSRP. Special order: call {PHONE} or request info online."[:320]}
        return
    lead = {"demo": "Demo", "used": "Used", "new": "New"}[kind]
    inp["seo"] = {"title": f"{lead} {title} for Sale | Ottawa, IL"[:70],
                  "description": (f"{lead} {title} for sale at Quest Watersports in Ottawa, IL — "
                                  + ("call for price" if call else f"${price:,.0f}")
                                  + f". Call {PHONE} or request info online.")[:320]}


def kind_of(inp):
    if "demo" in inp["tags"]:
        return "demo"
    return "used" if mf(inp, "condition") == "Pre-Owned" else "new"


def lead_paras(demo=False, consignment=False, qty=None, color=None):
    out = []
    if demo:
        out.append("<p><strong>Demo boat.</strong> This kayak was used for on-the-water demos and is sold as used.</p>")
    if consignment:
        out.append("<p><strong>Consignment.</strong> Quest Watersports is selling this boat on behalf of its owner.</p>")
    if qty and qty > 1:
        out.append(f"<p><strong>{qty} in stock</strong>" + (f": {color}." if color else ".") + "</p>")
    return "".join(out)


def apply_msrp(inp, msrp, rid, warnings, label="2027 MSRP"):
    v = inp["variants"][0]
    price = float(v["price"])
    if price < msrp:
        v["compareAtPrice"] = f"{msrp:.2f}"
        set_mf(inp, "msrp_label", label)
        if price < 0.8 * msrp - 0.005:
            warnings.append({"id": rid, "title": inp["title"], "price": price, "msrp_2027": msrp,
                             "lowest_allowed": round(0.8 * msrp, 2)})
    else:
        v.pop("compareAtPrice", None)
        set_mf(inp, "msrp_label", None)


def to_2027(rec, rid, spec):
    inp = copy.deepcopy(rec["input"])
    make = mf(inp, "make") or "Hobie"
    inp["title"] = f"2027 {make} {spec['model']}"
    inp["handle"] = f"{slugify(inp['title'])}-{rid}"
    set_tags(inp, add=["year:2027", "special-order"], remove=["year:*", "sale-pending"])
    for k, val in (("year", "2027"), ("model", spec["model"]), ("color", spec.get("colors")), ("stock_number", None),
                   ("availability_note", spec.get("availability")), ("msrp_label", None)):
        set_mf(inp, k, val)
    set_mf(inp, "special_order", "true", "boolean")
    set_mf(inp, "call_for_price", "false", "boolean")
    set_mf(inp, "sale_pending", "false", "boolean")
    base = {"inventoryPolicy": "DENY", "inventoryItem": {"tracked": True}, "taxable": True}
    if spec.get("drives"):
        inp["productOptions"] = [{"name": "MirageDrive", "values": [{"name": d} for d in spec["drives"]]}]
        inp["variants"] = [dict(base, optionValues=[{"optionName": "MirageDrive", "name": d}], price=f"{p:.2f}",
                                sku=f"QW-2027-{rid}-{d}") for d, p in spec["drives"].items()]
    else:
        inp["variants"] = [dict(base, optionValues=[{"optionName": "Title", "name": "Default Title"}],
                                price=f"{spec['price']:.2f}", sku=f"QW-2027-{rid}")]
    notes = "".join(f"<li>{u}</li>" for u in spec.get("updates", []))
    intro = (f"<p><strong>Special order: the 2027 {spec['model']} is not in stock.</strong> "
             f"Call {PHONE} or request info and we'll order one for you"
             + "." + (f" {spec['availability']}" if spec.get("availability") else "") + "</p>" + (f"<p>New for 2027:</p><ul>{notes}</ul>" if notes else "")
             + (f"<p>2027 colors: {spec['colors']}.</p>" if spec.get("colors") else ""))
    inp["descriptionHtml"] = intro + re.sub(r"\b2026\b", "2027", inp["descriptionHtml"])
    for f in inp.get("files", []):
        f["alt"] = re.sub(r"^New 2026", "Hobie 2027", f["alt"]).replace("2026", "2027")
    seo(inp, "special")
    return {"identifier": {"handle": inp["handle"]}, "input": inp, "source": dict(rec["source"], decision="to_2027")}


def manual(key, spec, records):
    title = f"{spec['year']} {spec['make']} {spec['model']}" + (" (Demo)" if spec.get("demo") else "")
    src = records.get(spec.get("photos_from") or "")
    used = spec["condition"] == "Pre-Owned"
    model_desc = src["input"]["descriptionHtml"] if src else ""
    if src:
        src_year = mf(src["input"], "year") or ""
        if src_year and src_year != spec["year"]:
            model_desc = model_desc.replace(src_year, spec["year"])
    price = spec.get("price") or 0
    variant = {"optionValues": [{"optionName": "Title", "name": "Default Title"}], "price": f"{price:.2f}",
               "sku": f"QW-{key}", "inventoryPolicy": "DENY", "inventoryItem": {"tracked": True}, "taxable": True}
    inp = {
        "title": title, "handle": slugify(title), "vendor": spec["make"], "productType": "Kayak",
        "descriptionHtml": lead_paras(spec.get("demo"), spec.get("consignment"), spec.get("qty"), spec.get("color"))
                           + (model_desc or f"<p>{'Used' if used else 'New'} {title}. Call {PHONE} for details.</p>"),
        "tags": ["inventory", "inventory-paddlesports", "inventory-pre-owned" if used else "inventory-new",
                 f"make:{spec['make']}", "type:Kayak", f"year:{spec['year']}"]
                + (["demo"] if spec.get("demo") else []) + (["consignment"] if spec.get("consignment") else []),
        "status": "DRAFT" if spec.get("draft") else "ACTIVE", "templateSuffix": "inventory",
        "productOptions": [{"name": "Title", "values": [{"name": "Default Title"}]}],
        "variants": [variant], "metafields": [],
    }
    for k, val in (("condition", spec["condition"]), ("year", spec["year"]), ("make", spec["make"]),
                   ("model", spec["model"]), ("color", spec.get("color")), ("inventory_id", f"manual:{key}")):
        set_mf(inp, k, val)
    if src:
        for k in ("length", "hull_type"):
            set_mf(inp, k, mf(src["input"], k))
        alt = ("Used " if used else "New ") + title
        inp["files"] = [dict(f, alt=alt + (f" photo {i + 1}" if i else "") + " (same model)") for i, f in enumerate(src["input"].get("files", []))]
    set_mf(inp, "call_for_price", "true" if spec.get("call") else "false", "boolean")
    set_mf(inp, "sale_pending", "false", "boolean")
    return {"identifier": {"handle": inp["handle"]}, "input": inp,
            "source": {"id": f"manual:{key}", "decision": "manual", "note": spec.get("note", "")}}


def locally_variants(rec, link):
    """Website listing: one variant per colour on hand, no UPC, never sellable online (0 stock; the owner
    can't collect card fees online). Returns the hidden "(In-Store Stock)" product that carries the
    UPCs at inventory 1, published only to Locally + Point of Sale."""
    inp = rec["input"]
    base = {k: v for k, v in inp["variants"][0].items() if k not in ("optionValues", "sku", "barcode")}
    inp["productOptions"] = [{"name": "Color", "values": [{"name": c} for c, _ in link]}]
    inp["variants"] = [dict(base, optionValues=[{"optionName": "Color", "name": c}], sku="W-" + upc, barcode=None) for c, upc in link]
    set_tags(inp, add=["in-stock"], remove=["locally"])
    set_mf(inp, "in_stock_list", json.dumps([c for c, _ in link]), "list.single_line_text_field")
    handle = rec["identifier"]["handle"] + "-in-store-stock"
    feed = {
        "title": inp["title"] + " (In-Store Stock)", "handle": handle, "vendor": inp["vendor"],
        "productType": inp["productType"], "status": "ACTIVE",
        "descriptionHtml": f"<p>Floor stock at Quest Watersports. Website listing: /products/{rec['identifier']['handle']}</p>",
        "tags": ["locally-feed", "in-store-stock"] + [t for t in inp["tags"] if t.startswith(("make:", "type:", "year:"))],
        "productOptions": inp["productOptions"],
        "variants": [dict(base, optionValues=[{"optionName": "Color", "name": c}], barcode=upc, sku=upc) for c, upc in link],
        "files": (inp.get("files") or [])[:1],
    }
    return {"identifier": {"handle": handle}, "input": feed, "stock": {upc: 1 for _, upc in link}}


def main():
    dec = json.load(open(os.path.join(INV, "kayak-decisions.json")))
    records = {os.path.basename(f)[:-5]: json.load(open(f)) for f in glob.glob(os.path.join(INV, "[0-9]*.json"))}
    os.makedirs(OUT, exist_ok=True)
    for f in glob.glob(os.path.join(OUT, "*.json")):
        os.remove(f)
    approved = set(dec["approved"]) | {k for k in dec["overrides"]}
    msrp, msrp_for = dec["msrp_2027"], dec["msrp_model_for_listing"]
    report = {"written": [], "excluded": [], "held": [], "pending": [], "map_warnings": [], "drafts": []}
    final = {}
    for rid, rec in sorted(records.items()):
        inp = rec["input"]
        if inp["productType"] == "eBike":
            report["excluded"].append(rid)  # e-bikes come from scripts/inventory/aventon.py, not the old site
            continue
        if inp["productType"] not in KAYAK_TYPES:
            final[rid] = rec
            continue
        if rid in dec["exclude"]:
            report["excluded"].append(rid)
            continue
        if rid in dec["hold"]:
            report["held"].append({"id": rid, "title": inp["title"], "why": dec["hold"][rid]})
            continue
        if rid in dec["to_2027"]:
            final[rid] = to_2027(rec, rid, dec["to_2027"][rid])
            continue
        if rid not in approved:
            report["pending"].append({"id": rid, "title": inp["title"], "url": rec["source"]["url"]})
            continue
        rec = copy.deepcopy(rec)
        inp = rec["input"]
        o = dec["overrides"].get(rid, {})
        if o.get("condition"):
            set_mf(inp, "condition", o["condition"])
            if o["condition"] == "Pre-Owned":
                set_tags(inp, add=["inventory-pre-owned"], remove=["inventory-new"])
        if o.get("demo"):
            set_tags(inp, add=["demo"])
            if not inp["title"].endswith("(Demo)"):
                inp["title"] += " (Demo)"
        if o.get("consignment"):
            set_tags(inp, add=["consignment"])
        if o.get("demo") or o.get("consignment"):
            inp["descriptionHtml"] = lead_paras(o.get("demo"), o.get("consignment")) + inp["descriptionHtml"]
        if o.get("color"):
            set_mf(inp, "color", o["color"])
        if o.get("price_from") and o["price_from"] in records:
            inp["variants"][0]["price"] = records[o["price_from"]]["input"]["variants"][0]["price"]
        is_hobie = mf(inp, "make") == "Hobie"
        if rid in msrp_for:
            apply_msrp(inp, msrp[msrp_for[rid]], rid, report["map_warnings"])
        elif inp["variants"][0].get("compareAtPrice"):
            set_mf(inp, "msrp_label", o.get("msrp_label") or ("Original MSRP" if mf(inp, "condition") == "Pre-Owned" else "MSRP"))
        if o:
            seo(inp, kind_of(inp))
        final[rid] = rec
    for key, spec in dec["manual"].items():
        if key.startswith("_"):
            continue
        rec = manual(key, spec, records)
        seo(rec["input"], "demo" if spec.get("demo") else "used" if spec["condition"] == "Pre-Owned" else "new")
        if spec.get("msrp") and spec.get("price") and spec["price"] < spec["msrp"]:
            apply_msrp(rec["input"], spec["msrp"], key, report["map_warnings"])
        if spec.get("draft"):
            report["drafts"].append({"key": key, "title": rec["input"]["title"], "why": spec.get("note", "")})
        final[f"m-{key}"] = rec
    feeds = {}
    for k, rec in final.items():
        link = dec.get("locally", {}).get(k if not k.startswith("m-") else "manual:" + k[2:])
        if link:
            feeds[k] = locally_variants(rec, link)
        map_scrub(rec["input"])
        json.dump(rec, open(os.path.join(OUT, f"{k}.json"), "w"), indent=1, ensure_ascii=False)
        report["written"].append({"key": k, "handle": rec["identifier"]["handle"], "title": rec["input"]["title"],
                                  "type": rec["input"]["productType"]})
    for k, feed in feeds.items():
        json.dump(feed, open(os.path.join(OUT, f"stock-{k}.json"), "w"), indent=1, ensure_ascii=False)
    report["in_store_stock_products"] = len(feeds)
    json.dump(report, open(os.path.join(OUT, "_report.json"), "w"), indent=1, ensure_ascii=False)
    print(f"written {len(report['written'])}  excluded {len(report['excluded'])}  held {len(report['held'])}  "
          f"pending {len(report['pending'])}  drafts {len(report['drafts'])}  MAP warnings {len(report['map_warnings'])}")


if __name__ == "__main__":
    main()
