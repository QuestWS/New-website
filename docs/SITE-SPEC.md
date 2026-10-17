# Quest Watersports — Shopify Theme & Content Spec

The repo root is a Shopify Online Store 2.0 theme (based on Dawn v15.4.1). It replaces the
WordPress site at https://www.questwatersports.com, ported into the Shopify store
`questws.myshopify.com`.

Priorities, in order: **mobile-first UX**, **SEO** (titles, descriptions, structured data,
semantic HTML, fast LCP), then fidelity to the original content.

## Business facts (use verbatim)

- Name: Quest Watersports (formerly Riverview Marine, Spring Valley IL, est. 1992; relocated to Ottawa and renamed in 2009)
- Address (display & schema): **1851 Old Chicago Rd, Ottawa, IL 61350** (next to Heritage Harbor Ottawa marina).
  Map/directions links use **1800 N 2871st Rd, Ottawa, IL 61350** (same building; Old Chicago Rd is poorly indexed by mapping services:
  `https://www.google.com/maps/dir/?api=1&destination=Quest+Watersports,+1800+N+2871st+Rd,+Ottawa,+IL+61350`).
  Never use "1851 N 2871st Rd" — it is a mix-up of the two.
  Heritage Harbor Marina: 1982 N 2753rd Road, Ottawa, IL 61350.
- Phone: 815.433.2200 (`tel:+18154332200`)
- Email: orders@questwatersports.com (store); hobie@questwatersports.com (paddlesports/Hobie)
- Facebook: https://www.facebook.com/QuestWS
- Hours (all seasons): Sales Tue–Sat 9:00 AM–5:00 PM; Sun & Mon by appointment only.
  Service Tue–Sat 8:00 AM–5:00 PM. Heritage Harbor Marina rentals: Sat–Sun, weather permitting (call 815-433-2200).
- Region: Starved Rock Country, Illinois River, I&M Canal Trail, Heritage Harbor Ottawa.
- External links: Member boat reservations https://www.boatcloud.com/stacktrack/access.aspx ·
  Payments https://pay.pospluslogin.com/questws · Winter storage deposits https://pay.pospluslogin.com/QuestWinter ·
  Heritage Harbor https://www.visitheritageharbor.com · Heritage Harbor boat rentals https://visitheritageharbor.com/welcome/rentals/ ·
  Aventon warranty https://www.aventon.com/pages/bike-registration

## Brand

- Colors: navy `#14293E` (primary/accent-1), gold `#C08A22` (accent-2), cream `#FDFCF7` (background),
  light blue `#EBF1F6` (alt background), text `#1D2B38`, white.
- Fonts: headings **Barlow Condensed** 600/700 (uppercase-ish, letter-spacing .02em); body **Source Sans 3** 400/600/700.
  Self-hosted woff2 in `assets/` (latin subset) with `font-display: swap`; preload heading font.
- Logo: shop image `shopify://shop_images/Questwetovalwithweb_0ec2ba7b-8de0-45e1-b739-3a11ad940280.png`.
- Header has a 4px gold bottom border.

## Shopify collections (handles) → where they appear

| Collection | Used on |
|---|---|
| `hobie-kayaks`, `hobie-itrek`, `old-town-kayaks`, `advanced-elements-in-stock`, `used-demo-kayaks`, `used-kayaks`, `kayak-parts` | Paddlesports pages, home |
| `sailboats`, `sailing-parts` | Sailing page |
| `ebikes`, `bike-parts` | eBike pages, home |
| `trailers`, `heritage-harbor-boating-supplies` | Boating / service pages |
| `mandatory-fees` | **Never** show in nav, search or featured sections (app-managed fees) |

## Page map (Shopify page handle ← WordPress source slugs → template suffix)

| Handle | Title | WP sources (migration/source/*.md) | Template |
|---|---|---|---|
| `boating` | Boats for Sale in Ottawa, IL | find-a-boat, boat-inventory, new-inventory, used-inventory | boating |
| `boat-club` | Quest Express Boat Club | boatclub, questexpress, learn-more | boat-club |
| `boat-club-faq` | Boat Club FAQs | questexpressfaqs | faq |
| `boat-club-testimonials` | Boat Club Member Testimonials | questexpress-testimonials, testimonials | landing |
| `member-login` | Member Reservations | member-reservation | landing |
| `illinois-river-boating` | Boating the Illinois River | boating-illinois-river | landing |
| `sell-or-trade` | Sell or Trade Your Boat, Kayak or Sailboat | sell-your-boat, sell-your-kayak, sell-your-sailboat-2 | contact |
| `service-and-parts` | Marine Service & Parts | service-and-parts, mechanical-services, service-request, parts-request | service |
| `valet-service` | Boat Valet Service | valet-service | service |
| `boat-storage` | Boat Storage & Off-Season Service | boat-storage, storage-form | service |
| `financing` | Boat, Kayak & Sailboat Financing | boat-financing, hobie-kayak-financing, finance-your-sailboat | landing |
| `sailing` | Hobie Sailboats & Sailing Gear | find-a-sailboat, sailboat-inventory | sailing |
| `inland-islanders` | Inland Islanders Hobie Island Club | inland-islanders | landing |
| `paddlesports` | Kayaks & Paddleboards | find-a-kayak, kayak-inventory, paddlesports-parts-accessories | paddlesports |
| `hobie-kayaks` | Hobie Kayak Dealer — Ottawa, IL | hobie-kayaks, hobie-models, hobie-inventory, hobie-eclipse | paddlesports |
| `used-kayaks` | Used & Demo Kayaks | used-hobie-kayaks, pre-owned-kayaks, used-hobie | paddlesports |
| `kayak-fishing` | Kayak Fishing | kayak-fishing | paddlesports |
| `kayak-rigging-and-demos` | Kayak Rigging & Demo Days | kayak-rigging, kayakdemo | paddlesports |
| `hobie-first-cast` | Hobie First Cast Program | hobie-first-cast | paddlesports |
| `stand-up-paddleboarding` | Stand-Up Paddleboarding | stand-up-paddleboarding | paddlesports |
| `rentals` | Kayak & Paddleboard Rentals | sup-kayak-rentals | rentals |
| `ebikes` | Electric Bikes in Starved Rock Country | find-a-ebike, ebike-inventory, ebikes-parts-accessories | ebikes |
| `ebike-rentals` | eBike Rentals | electric-bike-rentals | rentals |
| `ebike-regulations` | Illinois eBike Regulations | ebikeregulations | landing |
| `ebike-charging-network` | eBike Charging Network | ebike-charging-network | ebikes |
| `i-and-m-canal-trail` | I&M Canal Trail by eBike | i-and-m-canal-trail | ebikes |
| `rv-services` | Camper & RV Repair and Maintenance | rv-services | service |
| `about` | History & Philosophy | philosophy, home (story section) | landing |
| `meet-the-staff` | Meet the Staff | meet-the-staff | landing |
| `our-facility` | Our Facility | our-facility | landing |
| `employment` | Employment | employment | contact |
| `contact` | Contact, Hours & Directions | contacts, locations, store-hours | contact |
| `starved-rock-country` | Starved Rock Country | starved-rock-country | landing |

Existing Shopify page kept: `important-notice-about-quest-branded-kayaks`.
Old news posts → Shopify blog `news` (articles keep their WP slug as handle).
Pages only present on WP for dealer-inventory widgets (`specials`, `sold-inventory`, `inventory`,
`my-collection`, `collections`, `products`, newsletter pages, `sitemap`, `privacy-policy`) are
not migrated as pages; they redirect (see `migration/redirects.csv`).

## Page JSON format (`migration/pages/<handle>.json`)

```json
{
  "handle": "boat-club",
  "title": "Quest Express Boat Club",
  "template_suffix": "boat-club",
  "seo_title": "≤ 60 chars, includes primary keyword + 'Ottawa, IL' where natural",
  "seo_description": "140–160 chars, benefit-led, includes location",
  "body_html": "<p>…</p>",
  "faqs": [{"q": "…", "a": "<p>…</p>"}],
  "source_slugs": ["boatclub", "questexpress"],
  "images": ["https://www.questwatersports.com/wp-content/uploads/…jpg"]
}
```

Body HTML rules: no `<h1>` (the template renders the page title as H1); start sections at `<h2>`;
semantic `<p>`, `<ul>`, `<h2>/<h3>`; descriptive `alt` on every `<img>` with `loading="lazy"`;
internal links point at new Shopify URLs (`/pages/<handle>`, `/collections/<handle>`, `/blogs/news/<handle>`);
phone numbers as `tel:` links; no inline styles, no scripts, no iframes except YouTube
(`https://www.youtube-nocookie.com/embed/<id>`, wrapped in `<div class="video-embed">`, `loading="lazy"`, `title` attr).
Drop WordPress chrome (Google Tag Manager notes, "HERO", "Banner" labels, dealer inventory filter widgets,
my-garage modal text). Keep the business's own wording; tighten and fix typos, don't invent facts, prices or claims.
`faqs` is optional (only where the source has Q&A) and is rendered with FAQPage schema by the template.
