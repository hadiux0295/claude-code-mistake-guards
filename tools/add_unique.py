#!/usr/bin/env python3
"""Add a record without duplicates. If a record with exactly the same normalized title exists, the add fails (exit 1).
A record whose title is only similar gets a warning, not a block: blocking on similarity also blocks legitimate new records.
  python3 add_unique.py records.jsonl "title" "body"
"""
import difflib
import json
import os
import re
import sys
import unicodedata


def norm(title):
    t = unicodedata.normalize("NFKC", title).lower()
    return re.sub(r"[\s\W_]+", "", t)  # differences in spaces and punctuation count as the same title


def main(path, title, body):
    rows = [json.loads(l) for l in open(path, encoding="utf-8")] if os.path.exists(path) else []
    n = norm(title)
    for r in rows:
        if norm(r["title"]) == n:
            print(f"DUPLICATE: a record with the same title already exists → {r['title']!r}. Edit that record instead.", file=sys.stderr)
            return 1
    for r in rows:
        if difflib.SequenceMatcher(None, norm(r["title"]), n).ratio() >= 0.8:
            print(f"warning: a similar record exists → {r['title']!r} (adding anyway)", file=sys.stderr)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps({"title": title, "body": body}, ensure_ascii=False) + "\n")
    print("added")
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:4]))
