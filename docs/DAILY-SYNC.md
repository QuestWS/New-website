# Daily sync runbook (WordPress -> Shopify)

Goal: keep the Shopify store content in step with https://www.questwatersports.com while the old
site is still being edited. Detection is scripted (`scripts/sync/`); the writes are done by the
session with the Shopify MCP tools (`graphql_query`, `graphql_mutation`).
Read `docs/SITE-SPEC.md` first (page map, Body HTML rules, JSON format).

## Hard rules
- NEVER delete or modify products, orders, customers, or collection product membership.
- NEVER publish/unpublish/duplicate themes; do not edit theme files except `templates/index.json` text settings (homepage).
- NEVER delete pages/articles/files. Removed WP pages are only reported.
- Do not touch the page `important-notice-about-quest-branded-kayaks`.
- Be polite to the WP server: run the crawl once (it already throttles to 1 req/s and retries 403/429/5xx).

## Steps

### a) Detect
```
scripts/sync/run.sh            # ~2 min; prints "CHANGES: N"; report in scripts/sync/last-report.json
```
Report fields: `changed[] {slug, shopify_target, unified_diff}`, `new_urls[]`, `removed_urls[]`,
`new_images[] {slug,url}`, `failed[]` (fetch errors; ignore those pages today, they retry tomorrow).
Targets: `page:<handle>`, `article:<handle>`, `home`, `unmapped`.

### b) No changes
If `CHANGES: 0` (and `failed` is empty or only transient): skip step c (and do not run `--apply-snapshots`), but still do c2 (social) and c3 (Monday guide). If those produce nothing either, stop — nothing to commit.

### c) Apply changes
Read `scripts/sync/last-report.json`. Work through each item. Judge whether a diff is meaningful
(wording, prices, hours, phone, staff, dates, new/removed sections). Ignore pure inventory-widget or
markup noise: record it and move on (still counts as handled; snapshots get refreshed in step d).

**Changed `page:<handle>`**
1. Open `migration/pages/<handle>.json`; edit `body_html` (and `title`, `seo_title`, `seo_description`, `faqs`, `images` if affected) to reflect the change. Keep the Body HTML rules in SITE-SPEC (no `<h1>`, start at `<h2>`, alt text + `loading="lazy"`, internal links to new Shopify URLs, `tel:` links, don't invent facts). Change only what the diff supports.
   Note a page maps from several WP slugs (`source_slugs`); the diff covers one of them.
2. Look up the page id:
```graphql
query { pages(first: 1, query: "handle:<handle>") { nodes { id handle title templateSuffix } } }
```
3. Update (SEO title/description live in the `global` metafields `title_tag` / `description_tag`, NOT in a `seo` input field; `PageUpdateInput` has only body, handle, isPublished, metafields, publishDate, redirectNewHandle, templateSuffix, title):
```graphql
mutation($id: ID!, $page: PageUpdateInput!) {
  pageUpdate(id: $id, page: $page) {
    page { id handle updatedAt }
    userErrors { field message code }
  }
}
```
variables:
```json
{ "id": "gid://shopify/Page/123",
  "page": {
    "title": "<title>",
    "body": "<body_html>",
    "templateSuffix": "<template_suffix>",
    "metafields": [
      {"namespace": "global", "key": "title_tag", "type": "single_line_text_field", "value": "<seo_title>"},
      {"namespace": "global", "key": "description_tag", "type": "single_line_text_field", "value": "<seo_description>"}
    ] } }
```
   Always check `userErrors`; fix and retry once, else report the failure.
   FAQs (`faqs` in the JSON) are rendered by the template from page content/metafield as set up in the theme; if the theme reads them from a metafield, check how an existing page stores them (`pages(first:1,query:"handle:boat-club-faq"){nodes{metafields(first:20){nodes{namespace key value}}}}`) and mirror that.

**Changed `article:<handle>`** (blog "news")
```graphql
query { articles(first: 1, query: "handle:<handle>") { nodes { id handle blog { id handle } } } }
mutation($id: ID!, $article: ArticleUpdateInput!) {
  articleUpdate(id: $id, article: $article) { article { id handle } userErrors { field message code } }
}
```
`article`: `{ "title": "...", "body": "<html>", "summary": "<html>", "metafields": [ {global.title_tag}, {global.description_tag} as above ] }`. Mirror the edit into `migration/articles/<handle>.json`.

**New WP news post** (`new_urls` under `/news/<slug>/`): fetch the page text (`migration/`-style snapshot is in the fresh crawl; run `python3 -I scripts/sync/crawl.py --only news__<slug> --out <tmpdir> --urls-file /dev/null`), write `migration/articles/<slug>.json` following the format of existing files there, then:
```graphql
query { blogs(first: 5, query: "handle:news") { nodes { id handle } } }
mutation($article: ArticleCreateInput!) {
  articleCreate(article: $article) { article { id handle } userErrors { field message code } }
}
```
`article`: `{ "blogId": "gid://shopify/Blog/...", "title": "...", "handle": "<slug>", "body": "<html>", "summary": "...", "author": {"name": "Quest Watersports"}, "isPublished": true, "publishDate": "<original date if known>", "metafields": [SEO as above] }`.

**New core page** (`new_urls` not under /news/): read the snapshot, pick the closest template from SITE-SPEC (`paddlesports`, `ebikes`, `service`, `landing`, `contact`, `rentals`, ...), create `migration/pages/<handle>.json` (add the WP slug to `source_slugs`; if it clearly duplicates an existing page, instead add the slug to that page's `source_slugs` and merge the content). Skip pure dealer-inventory/widget/newsletter pages (see SITE-SPEC) and just report them. Then:
```graphql
mutation($page: PageCreateInput!) {
  pageCreate(page: $page) { page { id handle } userErrors { field message code } }
}
```
`page`: `{ "title", "handle", "body", "isPublished": true, "templateSuffix", "metafields": [SEO as above] }`.
Add it to the right menu (read first, then send back the FULL item list; omitting items deletes them):
```graphql
query { menus(first: 10) { nodes { id handle title items { id title type url resourceId items { id title type url resourceId items { id title type url resourceId } } } } } }
mutation($id: ID!, $title: String!, $items: [MenuItemUpdateInput!]!) {
  menuUpdate(id: $id, title: $title, items: $items) {
    menu { id handle } userErrors { field message code }
  }
}
```
Existing items are passed back with their `id`, `title`, `type`, `url`/`resourceId` and nested `items`; add `{ "title": "<title>", "type": "PAGE", "resourceId": "<page gid>" }` under the right parent. Never touch the `mandatory-fees` collection or remove existing links.

**Removed URLs**: do NOT delete or unpublish anything. List them in the commit body / final message; a human decides (redirects live in `migration/redirects.csv`).

**Homepage (`home`)**: summarize the diff in the final message. If the hero/intro text changed, update the matching text settings in `templates/index.json` (headings/subheadings/button labels only; keep structure and IDs). Navigation tiles and inventory widgets on WP are not mirrored.

**New images** (`new_images[]`, only for images belonging to content you updated): upload and use the returned CDN URL in the page body / JSON `images`:
```graphql
mutation($files: [FileCreateInput!]!) {
  fileCreate(files: $files) { files { id fileStatus alt ... on MediaImage { image { url } } } userErrors { field message code } }
}
```
variables: `{"files":[{"originalSource":"<WP image URL>","contentType":"IMAGE","alt":"<descriptive alt>"}]}`. The URL is available once processing finishes: re-query `node(id:"<file id>"){ ... on MediaImage { fileStatus image { url } } }` until `READY`.

### c1) Dealer inventory → Shopify products
1. `python3 -I scripts/inventory/build.py` — fetches the old site's inventory feed and writes one
   `productSet` payload per AVAILABLE unit to `migration/inventory/<id>.json` (+ `_index.json` with every
   feed id and its Available/Sold status).
2. Compare with the previous commit (`git diff --stat migration/inventory`):
   - **New available id** (no product with handle ending `-<id>` yet): run `productSet` with the file's
     `identifier` + `input` (synchronous: true), then `publishablePublish` to the Online Store
     (publication `gid://shopify/Publication/70750208175`).
     EXCEPTION — kayaks/paddleboards (tag `inventory-paddlesports`): the owner reconciles kayak stock by hand
     (`migration/inventory/kayak-reconciliation.md`). Do not create new kayak products; list them in the
     final message for the owner to approve.
   - **Changed file** for an existing product (price, description, photos, sale-pending): re-run `productSet`
     with the same handle identifier (it updates in place).
   - **Id now "Sold"** (or gone from the feed) and a product exists: `productUpdate(product:{id, status: ARCHIVED})`.
     Never delete products.
3. Units are never purchasable online: keep `inventoryPolicy: DENY`, tracked, 0 on hand (build.py does this).
   Smart collections `inventory`, `inventory-boats`, `inventory-paddlesports`, `inventory-sailboats`,
   `inventory-ebikes`, `inventory-pre-owned` pick products up by tag automatically.

### c2) Social media → blog (Facebook / Instagram)
Only if the environment variable `META_ACCESS_TOKEN` is set (a long-lived Page access token with
`pages_read_engagement`, `pages_read_user_content`, `instagram_basic`). Optional `META_PAGE_ID`
(Facebook Page id for facebook.com/QuestWS) and `META_IG_USER_ID` (Instagram business account
for instagram.com/kayakquest); if missing, discover them with
`GET https://graph.facebook.com/v21.0/me/accounts?fields=id,name,instagram_business_account`.
Never print the token.

1. Fetch the last 2 days of posts:
   - Facebook: `GET /v21.0/$META_PAGE_ID/posts?fields=id,message,created_time,permalink_url,full_picture&since=<unix ts>`
   - Instagram: `GET /v21.0/$META_IG_USER_ID/media?fields=id,caption,media_type,media_url,permalink,timestamp`
2. Keep a ledger in `migration/social-ledger.json` (`{"<platform>:<id>": "<article handle or 'skipped'>"}`) so nothing is processed twice.
3. Turn a post into a blog article (blog `news`, tag `Social` + topic tag) only when it is substantive:
   an event, demo day, new arrival/model, boat club news, a trip report or a promotion with
   enough text for 150+ words. Rewrite the caption into a short article (H2s, a link to the most
   relevant /pages/ or /collections/ handle, a closing call-to-action with `tel:+18154332200`),
   upload the photo with `fileCreate` (originalSource = `full_picture`/`media_url`, never hotlink),
   and set SEO title/description metafields. Short or purely promotional posts → ledger `skipped`.
4. Credit the original: end the article with “Originally shared on our [Facebook|Instagram]” linking the permalink.

### c3) Weekly SEO guide
On Mondays only, write one new evergreen guide (900–1400 words) for blog `news`, tag `Guides`,
following the format of `migration/articles/*-guide*.json` (FAQ section + `faqs` list,
3–6 internal links to existing handles, SEO title ≤60 chars, description 140–160 chars).
Pick a topic not yet covered (check existing article handles), relevant to the season and to
what the store sells (search products read-only first). Never invent prices, laws or policies;
verify outside facts with WebSearch and hedge when unverifiable. Save it to
`migration/articles/<handle>.json` and create it with `articleCreate` (published).

### d) Snapshot, commit, push
```
scripts/sync/run.sh --apply-snapshots    # refreshes migration/source/*.md and migration/source-urls.txt
git add -A migration docs templates scripts/sync/last-report.json
git commit -m "Daily sync: $(date +%F) — N changes"      # N from "CHANGES: N"
git push -u origin <current branch>
```
Do the apply step only after the Shopify writes succeeded; if some failed, still apply but list the failures in the commit body so they are retried by hand.
If the push fails on network error, retry up to 4 times (2s, 4s, 8s, 16s).

### e) Final message
Short summary: pages/articles updated, new items created, removed URLs (report only), homepage notes, failures.

## Notes
- Scripts use Python 3 stdlib + bs4 (run.sh installs beautifulsoup4 if missing); run with `python3 -I`.
- If run.sh prints `SYNC FAILED: ...` (exit 1), do NOT treat it as "no changes": report the failure in the final message.
- `crawl.py --out DIR [--limit N] [--only slug,..]` for ad-hoc fetches; `diff.py FRESH_DIR [--old DIR]` for ad-hoc diffs.
- `diff.py` normalises away: Google Tag Manager lines, copyright lines, inventory/result counts, "Showing x-y of z", whitespace.
- If the crawl gets 403s despite backoff, re-run later; a partial/failed crawl never overwrites snapshots of pages it could not fetch (failed pages are simply absent from the fresh dir). A crawl that finds no sitemap URLs is not applied.

## Store and schedule reference
- Scheduled task: "Quest daily site sync", every day 5:47 AM America/Chicago, fresh session per run, push + email notifications.
  It needs the Shopify connector and this repo attached (edit the scheduled task at claude.ai) to write to the store.
- Shopify: blog "News & Guides" (handle `news`, gid://shopify/Blog/75924603055); menus `quest-main-menu`, `quest-footer-explore`, `footer`.
- Theme in store: "Quest Watersports 2026" (gid://shopify/OnlineStoreTheme/159661129950), uploaded from this repo.
  Push later theme changes to it with `themeFilesUpsert` (allowed while it is unpublished) or connect this branch with Shopify's GitHub integration.
- Content image map (old WordPress URL → Shopify CDN): `migration/image-map.json`.
