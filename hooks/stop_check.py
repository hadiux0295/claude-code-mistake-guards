#!/usr/bin/env python3
"""Reply check (Stop hook). Reads Claude's reply the moment it tries to finish, and makes it rewrite the reply
if it contains a claim that has already been wrong before.

One rule = one wrong claim that came up at least twice. If one sentence contains the claim, and the 'fact that must
come with it' is not nearby (200 characters before or after), the stop is blocked. The reason becomes Claude's next
instruction, so it fixes the reply and answers again.
Override: put REPLY_OK=<rule name> in the reply and give the reason. After one block (stop_hook_active) it never blocks again.
"""
import json
import re
import sys

RULES = [
    # (name, claim patterns — all must appear in one sentence, fact pattern that must be nearby, message when blocked)
    ("web_over_own_record",
     [r"search results|\bblogs?\b|\bforums?\b|\breddit\b|according to (the )?(web|internet|posts?|articles?)|people (say|report)|online (posts|sources|reports)",
      r"\beligib|\bregion|\bcountr|\bsign[ -]?up|\baccounts? (from|in|are|can)|\bnot (allowed|supported|available)"],
     r"our (own )?(record|log|note)|we (checked|tested|measured|signed up)|(checked|tested|measured) (it )?(directly|ourselves)|in (my|our) account",
     "You judged account / eligibility / region from web search results. Look for our own measured record first; if they disagree, follow the record."),
    ("traffic_source",
     [r"\btraffic|\bvisit|\bviews?\b|\busers?\b|\breferr", r"\bgr[eo]w|\bincreas|\brose\b|\bjump|\bdoubl|\bdemand|\bsignal"],
     r"\bbots?\b|crawler|user.?agent|our own (visit|traffic)|ourselves|excluding (my|our)",
     "You read a traffic / user number as demand. Separate bots and your own visits first, then say it."),
]
SENT = re.compile(r"[.!?]\s|\n+")


def check(text):
    for name, claims, fact, msg in RULES:
        if f"REPLY_OK={name}" in text:
            continue
        pos = 0
        for m in SENT.finditer(text + "\n"):
            s, start = text[pos:m.start()], pos
            pos = m.end()
            if all(re.search(c, s, re.I) for c in claims):
                near = text[max(0, start - 200): start + len(s) + 200]
                if not re.search(fact, near, re.I):
                    return f"[{name}] {msg} (if it is still right, put REPLY_OK={name} and the reason in the reply)"
    return None


try:
    p = json.load(sys.stdin)
    if not p.get("stop_hook_active"):  # already blocked once and rewriting → pass (prevents an endless loop)
        reason = check(p.get("last_assistant_message") or "")
        if reason:
            print(json.dumps({"decision": "block", "reason": reason}))
except Exception as e:
    print(f"[stop_check] checker error, passing: {e}", file=sys.stderr)
sys.exit(0)
