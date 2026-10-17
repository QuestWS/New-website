#!/usr/bin/env python3
"""Build the `files` argument for Shopify's themeFilesUpsert mutation.

Each file is fetched by Shopify from raw.githubusercontent.com at a pushed commit,
so the payload stays small. Usage:
  python3 scripts/deploy/upsert-payload.py <sha> path [path ...]
  python3 scripts/deploy/upsert-payload.py <sha> --since <ref>   # theme files changed since ref
Prints JSON chunks of at most 50 files (the mutation's limit).
"""
import json, subprocess, sys

THEME_DIRS = ("assets/", "config/", "layout/", "locales/", "sections/", "snippets/", "templates/")
REPO = "questws/new-website"

def main():
    sha, rest = sys.argv[1], sys.argv[2:]
    if rest[:1] == ["--since"]:
        out = subprocess.check_output(["git", "diff", "--name-only", "--diff-filter=AM", rest[1], sha], text=True)
        paths = [p for p in out.split() if p.startswith(THEME_DIRS)]
    else:
        paths = rest
    files = [{"filename": p, "body": {"type": "URL", "value": f"https://raw.githubusercontent.com/{REPO}/{sha}/{p}"}} for p in paths]
    for i in range(0, len(files), 50):
        print(json.dumps(files[i:i + 50]))

if __name__ == "__main__":
    main()
