#!/usr/bin/env python3
"""Short-save guard (PreToolUse · an MCP save tool). Denies a too-short body sent to a save tool that overwrites the whole record.

In practice a short body was almost always a placeholder sent to "see what the tool returns". If that save goes through,
the whole record becomes the placeholder.
Set MIN a little below the shortest body you have legitimately saved (measure your past records first).
Override: put SHORT_OK in the body and say why. A bug in this script lets the save through.
"""
import json
import sys

MIN = 300                 # bodies shorter than this are denied
FIELD = "content"         # the argument that carries the body for that tool (differs per tool: content, text, body …)

try:
    p = json.load(sys.stdin)
    body = str((p.get("tool_input") or {}).get(FIELD) or "")
    if len(body.strip()) < MIN and "SHORT_OK" not in body:
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": (
                f"The body is {len(body.strip())} characters, shorter than {MIN}. This save overwrites the whole record. "
                "If you want to look a value up, use the read tool (get / search); when saving, send the full merged body. "
                "If this really is a short record, put SHORT_OK in the body and say why.")}}))
except Exception as e:
    print(f"[guard_short_save] checker error, passing: {e}", file=sys.stderr)
sys.exit(0)
