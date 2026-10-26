#!/usr/bin/env python3
"""Command guard (PreToolUse · Bash). Runs right before Claude executes a shell command and denies it if a rule matches.

One rule = one mistake that actually happened. When a new mistake repeats, don't add a new hook: add one entry to RULES.
Override: put GUARD_OK=<rule name> inside the command and have the agent say why in its reply.
If this script itself has a bug, it lets the command through (a broken checker that stops every command is worse).
"""
import json
import os
import re
import shlex
import sys

# ── Values to adapt to your setup ─────────────────────────────────────────
BLOCKED_SITES = ["example-market.com"]          # sites never to open headlessly (their bot block hits your whole network)
ALLOWED_API_HOSTS = ["api.example-market.com"]  # the official API host of the same site stays allowed
SAFE_PULL = "scripts/safe_pull.sh"              # the command to use instead of a bare git pull
UPLOAD_ROOT = os.path.expanduser(os.environ.get("GUARD_UPLOAD_ROOT", "~/Uploads"))  # folder a human picks files from
UPLOAD_TRACKS = {"archive", "handoff"}          # top-level folders allowed there (add your project/track folder names)
STATE_DIR = os.path.join(os.environ.get("CLAUDE_PROJECT_DIR", "."), ".claude", "guard_state")
FIRST_COMMIT_LINE = "said:"                     # prefix of a line the first commit of each session must carry
# ──────────────────────────────────────────────────────────────────────────


def rule_self_kill(cmd, p):
    """Deny pkill -f always, and pgrep -f when its result drives a condition or a wait loop. The pattern also appears
    in the command line of the shell running this command, so it kills its own shell or finds itself forever."""
    if re.search(r"\bpkill\b[^;&|]*\s-\w*f", cmd):
        return "pkill -f also kills the shell running this command. Kill by PID file, or wrap one letter of the pattern: [s]erver."
    if re.search(r"\b(if|while|until)\b[^;]*\bpgrep\b[^;&|]*\s-\w*f|\bpgrep\b[^;&|]*\s-\w*f[^;&|]*(&&|\|\|)", cmd):
        if not re.search(r"pgrep\b[^;&|]*'?\[[^\]]+\]", cmd):
            return "pgrep -f matches its own shell, so the wait never ends. Wrap one letter of the pattern: [s]erver."
    return None


def rule_bare_pull(cmd, p):
    """Deny a bare git pull in this repo (only the agreed safe pull script is allowed)."""
    if re.search(r"(^|[;&|(]\s*|\bthen\s+|\bdo\s+)git\s+(-C\s+\S+\s+)?pull\b", cmd) and SAFE_PULL not in cmd:
        return f"In this repo use {SAFE_PULL} instead of a bare git pull."
    return None


def rule_blocked_site(cmd, p):
    """Deny opening a BLOCKED_SITES web page with a headless browser or curl/wget. The official API host passes."""
    if not re.search(r"\b(curl|wget|playwright|chromium|puppeteer)\b|--headless", cmd):
        return None
    for host in re.findall(r"https?://([a-z0-9.-]+)", cmd, re.I):
        host = host.lower()
        if host in ALLOWED_API_HOSTS:
            continue
        if any(host == s or host.endswith("." + s) for s in BLOCKED_SITES):
            return f"Don't open {host} web pages automatically (its bot block hits the whole network). Use the official API or a human's screenshot."
    return None


def _destinations(cmd):
    """Roughly extract destination paths of cp / mv / mkdir. Quotes are resolved with shlex; paths containing $VAR are unknown and skipped."""
    out = []
    for seg in re.split(r"&&|\|\||;|\|", cmd):
        try:
            toks = shlex.split(seg)
        except ValueError:
            continue
        if not toks or toks[0] not in ("cp", "mv", "mkdir"):
            continue
        args = [t for t in toks[1:] if not t.startswith("-")]
        if not args or any("$" in a for a in args):
            continue
        if toks[0] == "mkdir":
            out += [("mkdir", None, os.path.expanduser(a)) for a in args]
        elif len(args) >= 2:
            dst = os.path.expanduser(args[-1])
            out += [(toks[0], os.path.expanduser(src), dst) for src in args[:-1]]
    return out


def rule_upload_layout(cmd, p):
    """Deny scattering files or creating new folders at the top of the human's upload folder, and deny putting a new
    file in a subfolder while an old file with the same name sits at the top (the human uploads the old one they see first)."""
    root = os.path.normpath(UPLOAD_ROOT)
    for verb, src, raw in _destinations(cmd):
        dst = os.path.normpath(raw)
        if not dst.startswith(root + os.sep) and dst != root:
            continue
        rel = os.path.relpath(dst, root).split(os.sep) if dst != root else []
        to_dir = verb != "mkdir" and (raw.endswith("/") or os.path.isdir(dst))  # copying into a folder keeps the source name
        if verb != "mkdir" and (not rel or (len(rel) == 1 and not to_dir)):
            return f"Don't put files directly at the top of {UPLOAD_ROOT}. Put them under a track folder."
        if rel and rel[0] not in UPLOAD_TRACKS:
            return f"{UPLOAD_ROOT}/{rel[0]} is not an allowed top-level folder. Use <track>/<try>/ under a track folder."
        sub = rel if to_dir else rel[:-1]  # folder the file lands in = <track>/<sub...>
        if verb != "mkdir" and len(sub) >= 2 and not sub[1].startswith("_old"):
            name = os.path.basename(src) if to_dir else rel[-1]
            if os.path.exists(os.path.join(root, rel[0], name)):
                return (f"{rel[0]}/{name} already exists at the top. The human will upload that old file. "
                        f"Move the old file to {rel[0]}/_old_<date>/ first, then put the new one at the top.")
    return None


def rule_first_commit_line(cmd, p):
    """Deny the first git commit of a session if its message lacks a FIRST_COMMIT_LINE line. Once passed, the session is not asked again."""
    sid = p.get("session_id")
    if not sid or not re.search(r"\bgit\s+commit\b", cmd):
        return None
    mark = os.path.join(STATE_DIR, f"{re.sub(r'[^A-Za-z0-9_-]', '_', sid)}.said")
    if os.path.exists(mark):
        return None
    if FIRST_COMMIT_LINE in cmd:
        os.makedirs(STATE_DIR, exist_ok=True)
        open(mark, "w").close()
        return None
    return (f"This is the session's first commit. Add a line '{FIRST_COMMIT_LINE} <the priority you stated in your first reply>' to the message. "
            "If you never stated it, tell the user now first.")


RULES = [  # (name, check) — the name is also the override token GUARD_OK=<name>
    ("self_kill", rule_self_kill),
    ("bare_pull", rule_bare_pull),
    ("blocked_site", rule_blocked_site),
    ("upload_layout", rule_upload_layout),
    ("first_commit_line", rule_first_commit_line),
]


def main():
    p = json.load(sys.stdin)
    if p.get("tool_name") != "Bash":
        return
    cmd = (p.get("tool_input") or {}).get("command") or ""
    reasons = []
    for name, fn in RULES:
        if f"GUARD_OK={name}" in cmd:
            continue
        try:
            r = fn(cmd, p)
        except Exception as e:  # a bug in one rule skips only that rule
            print(f"[guard_bash] {name} error, passing: {e}", file=sys.stderr)
            continue
        if r:
            reasons.append(f"[{name}] {r} (if you really need it, put GUARD_OK={name} in the command and say why)")
    if reasons:
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": "\n".join(reasons)}}))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # the checker itself broke → don't block
        print(f"[guard_bash] checker error, passing: {e}", file=sys.stderr)
    sys.exit(0)
