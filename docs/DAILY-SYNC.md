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
If `CHANGES: 0` (and `failed` is empty or only transient): stop. Nothing to commit. (Do not run `--apply-snapshots`.)

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
- Scripts use Python 3 stdlib + bs4 only; run with `python3 -I`.
- `crawl.py --out DIR [--limit N] [--only slug,..]` for ad-hoc fetches; `diff.py FRESH_DIR [--old DIR]` for ad-hoc diffs.
- `diff.py` normalises away: Google Tag Manager lines, copyright lines, inventory/result counts, "Showing x-y of z", whitespace.
- If the crawl gets 403s despite backoff, re-run later; a partial/failed crawl never overwrites snapshots of pages it could not fetch (failed pages are simply absent from the fresh dir). A crawl that finds no sitemap URLs is not applied.
