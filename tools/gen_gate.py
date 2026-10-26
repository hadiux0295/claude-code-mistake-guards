#!/usr/bin/env python3
"""Gatekeeper for a generation pipeline. Filters input rows before generating, and stops at the end if any fallback happened.

The default is 'blocked'. Writing a warning to a log blocks nothing (nobody reads batch logs).
  python3 gen_gate.py rows.json                    exit 2 if even one fallback happened
  python3 gen_gate.py rows.json --allow-fallback   passes only when a human knowingly allows it
rows.json example: [{"id": "c1", "kind": "story", "airport": "ICN", "year": 1998},
                    {"id": "tile1", "kind": "tile", "base_image": ""}]
"""
import json
import sys

# Fact table: start with the values that were actually wrong (don't try to fill it all; add what got caught).
OPENED = {"ICN": 2001, "GMP": 1958}   # airport code → year it opened


def validate(row):
    """Return a reason to block before generating. None means it may be generated."""
    if row.get("airport") in OPENED and row.get("year") and row["year"] < OPENED[row["airport"]]:
        return f"{row['airport']} opened in {OPENED[row['airport']]} — no departure possible in {row['year']}"
    if row.get("kind") == "tile" and not row.get("base_image"):
        return "tile fill without a base image — the tool fills it with its default pattern"
    return None


def generate(row):
    """Where real generation happens (simulated here). With too little source material it substitutes a generic answer and says so."""
    used_fallback = not row.get("source")
    return {"id": row["id"], "text": "generic answer" if used_fallback else "answer grounded in the source"}, used_fallback


def main(path, allow_fallback):
    rows = json.load(open(path, encoding="utf-8"))
    out, fallbacks, blocked = [], [], 0
    for row in rows:
        why = validate(row)
        if why:
            print(f"BLOCKED {row.get('id')}: {why}")
            blocked += 1
            continue
        result, fb = generate(row)
        out.append(result)
        if fb:
            fallbacks.append(row["id"])
    print(f"generated {len(out)} · blocked {blocked} · fallback {len(fallbacks)}")
    if fallbacks and not allow_fallback:
        print(f"STOP: {len(fallbacks)} fallback answer(s) ({', '.join(fallbacks)}). Fill the source or allow it with --allow-fallback.",
              file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], "--allow-fallback" in sys.argv[2:]))
