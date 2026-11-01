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
# Out of the box only self_kill is on. Each other rule stays off until its value is set (edit here, or set the env var).
def _env_list(name):
    return [s.strip().lower() for s in os.environ.get(name, "").split(",") if s.strip()]


BLOCKED_SITES = _env_list("GUARD_BLOCKED_SITES")          # e.g. ["example-market.com"]: sites never to open headlessly
ALLOWED_API_HOSTS = _env_list("GUARD_ALLOWED_API_HOSTS")  # e.g. ["api.example-market.com"]: that site's official API stays allowed
SAFE_PULL = os.environ.get("GUARD_SAFE_PULL", "")         # e.g. "scripts/safe_pull.sh": the command to use instead of a bare git pull
UPLOAD_ROOT = os.path.expanduser(os.environ.get("GUARD_UPLOAD_ROOT", ""))  # e.g. "~/Uploads": folder a human picks files from
UPLOAD_TRACKS = set(_env_list("GUARD_UPLOAD_TRACKS")) or {"archive", "handoff"}  # top-level folders allowed there
STATE_DIR = os.path.join(os.environ.get("CLAUDE_PROJECT_DIR", "."), ".claude", "guard_state")
FIRST_COMMIT_LINE = os.environ.get("GUARD_FIRST_COMMIT_LINE", "")  # e.g. "said:": a line the session's first commit must carry
# ──────────────────────────────────────────────────────────────────────────


def _self_matching(args, text):
    """args = the text after pkill/pgrep/pidwait, text = the whole command. The Bash tool runs the command as
    bash -c "... eval '<the whole command>'", so that shell's own command line holds the whole text. True if -f is used
    without -A (--ignore-ancestors) and the pattern matches that text. A bracket ([s]erver) only helps while the
    plain word appears nowhere else: `cd /srv/server && pkill -f '[s]erver'` still matches its own shell."""
    try:
        toks = shlex.split(args)
    except ValueError:
        toks = args.split()
    full, ancestors_off, pat, i = False, False, None, 0
    while i < len(toks):
        t = toks[i]
        if t == "--full":
            full = True
        elif t == "--ignore-ancestors":
            ancestors_off = True
        elif t in ("-u", "-U", "-g", "-G", "-P", "-s", "-t", "-F", "-d", "-r", "-O", "--signal", "--pidfile"):
            i += 1
        elif re.match(r"^-[A-Za-z]+$", t):
            full = full or "f" in t
            ancestors_off = ancestors_off or "A" in t
        elif not t.startswith("-"):
            pat = t
            break
        i += 1
    if not full or ancestors_off or pat is None or "$" in pat:  # a $VARIABLE pattern is unknown here: let it through
        return False
    try:
        return re.search(pat, text) is not None
    except re.error:
        return pat in text


def rule_self_kill(cmd, p):
    """Deny pkill/pidwait -f, and pgrep -f whose result is used (a condition, a wait loop, $(...), | xargs kill), when
    the pattern matches this command's own text: the shell running it gets killed (exit 143/144) or the wait finds
    itself forever. A display-only `pgrep -af x` just shows one extra line. Fix = -A (procps-ng 4.0.3+)."""
    text = cmd  # what the shell's own command line holds, heredoc bodies included
    # heredoc bodies written to a file are text, not commands (a body fed to a local bash/sh runs inside this same shell, so it stays)
    cmd = re.sub(r"(?ms)^([^\n]*?)<<-?\s*(['\"]?)(\w+)\2([^\n]*\n)(.*?)^\s*\3\s*$",
                 lambda h: h.group(0) if re.search(r"\b(bash|sh|zsh)\b", h.group(1)) and not re.search(r"\bssh\b", h.group(1)) else h.group(1) + h.group(4), cmd)
    # only at a command position (start, after ; && || | ( $( `, a shell keyword, sudo, bash -c ' or ssh host '), not inside echo "..."
    for m in re.finditer(r"(?:^|[;&|(`\n]|\$\(|\b(?:then|do|if|while|until|sudo)\s|!\s|-c\s+['\"]|\bssh\b[^'\";&|]*['\"])\s*(pkill|pgrep|pidwait)\b([^;&|)`'\"\n]*(?:['\"][^'\"]*['\"][^;&|)`\n]*)?)", cmd):
        if not _self_matching(m.group(2), text):
            continue
        if m.group(1) in ("pkill", "pidwait"):
            return (f"{m.group(1)} -f: the pattern matches this command's own text, which is the command line of the shell running it, "
                    f"so that shell is hit (exit 143/144). Add -A (--ignore-ancestors, procps-ng 4.0.3+): {m.group(1)} -A -f ... "
                    "Without -A: bracket one letter ([s]erver.js) and keep the plain word out of the rest of the command (paths, echo), or kill by PID file.")
        before, after = cmd[:m.start(1)], cmd[m.end():]
        used = (re.search(r"(\b(if|while|until)\b|!|\$\(|`)\s*$", before)
                or re.match(r"\s*(&&|\|\||\|\s*xargs\b|>\s*/dev/null)", after)
                or re.search(r"\b(if|while|until)\b[^;]*$", before)
                or re.search(r"(^|[^2])>\s*/dev/null", m.group(2)))  # stdout hidden = only the exit status is used
        if used:
            return ("pgrep -f: the pattern matches this command's own text, so it finds the shell running it (the wait never ends, "
                    "the kill hits the shell). Add -A (procps-ng 4.0.3+): pgrep -A -f ..., or bracket one letter and keep the plain word out of the command.")
    return None


def rule_bare_pull(cmd, p):
    """Deny a bare git pull in this repo (only the agreed safe pull script is allowed). Off until SAFE_PULL is set."""
    if not SAFE_PULL:
        return None
    if re.search(r"(^|[;&|(]\s*|\bthen\s+|\bdo\s+)git\s+(-C\s+\S+\s+)?pull\b", cmd) and SAFE_PULL not in cmd:
        return f"In this repo use {SAFE_PULL} instead of a bare git pull."
    return None


def rule_blocked_site(cmd, p):
    """Deny opening a BLOCKED_SITES web page with a headless browser or curl/wget. The official API host passes."""
    if not BLOCKED_SITES:
        return None
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
    if not UPLOAD_ROOT:
        return None
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
    if not FIRST_COMMIT_LINE or not sid or not re.search(r"\bgit\s+commit\b", cmd):
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
