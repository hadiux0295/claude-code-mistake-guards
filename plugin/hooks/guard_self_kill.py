#!/usr/bin/env python3
"""Self-kill guard (PreToolUse · Bash). Runs right before Claude executes a shell command and denies
pkill/pidwait -f, and pgrep -f whose result is used, when the pattern matches the command's own text.

Why: the Bash tool runs the command as bash -c "... eval '<the whole command>'", so that shell's own
command line holds the whole text. `pkill -f server.js` then hits the shell running it (exit 143/144).
A bracket ([s]erver) only helps while the plain word appears nowhere else: `cd /srv/server && pkill -f '[s]erver'`
still matches its own shell. -A (--ignore-ancestors, procps-ng 4.0.3+) skips this shell's ancestors only: a loop, group or
shell function piped next to pgrep runs in a fork that still matches, and so does any other tool shell whose text names the
target. Best fix = anchor the pattern at the start of the target's command line ('^node server.js'): tool shells start
with /bin/bash -c, so they never match (anthropics/claude-code#93607, martin152's cases).

Reads only the tool call on stdin. Nothing else is read; no network, no files written.
Override one command: put GUARD_OK=self_kill inside it and say why.
If this script itself breaks, the command goes through (a broken checker that stops every command is worse).
"""
import json
import re
import shlex
import sys


def _self_matching(args, text):
    """args = the text after pkill/pgrep/pidwait, text = the shell's own command line.
    "plain" if -f is used without -A and the pattern matches that text, "ancestors" if it matches with -A, else None."""
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
    if not full or pat is None or "$" in pat:  # a $VARIABLE pattern is unknown here: let it through
        return None
    try:
        hit = re.search(pat, text) is not None
    except re.error:
        hit = pat in text
    return ("ancestors" if ancestors_off else "plain") if hit else None


# A pipeline stage that runs in a fork of the tool's shell instead of exec'ing a program: a loop, a { } / ( ) group,
# or a shell function (in the Bash tool, grep, rg, find and pkill are functions from the shell snapshot).
# That fork keeps the shell's command line and is a sibling of pgrep, not an ancestor, so -A does not skip it.
_FORKED_STAGE = r"\s*(?:(?:while|until|for|if|case|select|grep|rg|find|pkill)\b|[{(])"


def _forked_neighbour(before, after):
    """True if the pipeline around the match has a stage that runs in a fork of this shell."""
    sep = r"\|\||&&|;|\n|&(?!&)"
    right = re.split(sep, after, maxsplit=1)[0].split("|")[1:]
    left = re.split(sep, before)[-1].split("|")[:-1]
    return (any(re.match(_FORKED_STAGE, st) for st in right)
            or any(re.match(_FORKED_STAGE, st) or re.search(r"(\}|\)|\bdone|\bfi|\besac)\s*$", st) for st in left))


def _claude_dir(p):
    """The user's ~/.claude, taken from the transcript path Claude Code sends with the call."""
    tp = p.get("transcript_path") or ""
    i = tp.find("/.claude/")
    return tp[:i + len("/.claude")] if i >= 0 else "/home/user/.claude"


def check(cmd, p):
    """Return the deny reason, or None."""
    # the shell's own command line: the tool's wrapper around the whole command, heredoc bodies included
    # (wrapper shape as quoted in anthropics/claude-code#93607)
    snap = _claude_dir(p) + "/shell-snapshots/snapshot-bash-0-x.sh"
    text = (f"/bin/bash -c source {snap} || true && shopt -u extglob || true && "
            "{ builtin unalias -- 'unsetenv'; builtin unset -f -- 'unsetenv'; } >/dev/null || true && "
            f"eval '{cmd}' < /dev/null && pwd -P >| /tmp/claude-0-cwd")
    # heredoc bodies written to a file are text, not commands (a body fed to a local bash/sh runs inside this same shell, so it stays)
    cmd = re.sub(r"(?ms)^([^\n]*?)<<-?\s*(['\"]?)(\w+)\2([^\n]*\n)(.*?)^\s*\3\s*$",
                 lambda h: h.group(0) if re.search(r"\b(bash|sh|zsh)\b", h.group(1)) and not re.search(r"\bssh\b", h.group(1)) else h.group(1) + h.group(4), cmd)
    # only at a command position (start, after ; && || | ( $( `, a shell keyword, sudo, bash -c ' or ssh host '), not inside echo "..."
    for m in re.finditer(r"(?:^|[;&|(`\n]|\$\(|\b(?:then|do|if|while|until|sudo)\s|!\s|-c\s+['\"]|\bssh\b[^'\";&|]*['\"])\s*(pkill|pgrep|pidwait)\b([^;&|)`'\"\n]*(?:['\"][^'\"]*['\"][^;&|)`\n]*)?)", cmd):
        hit = _self_matching(m.group(2), text)
        if not hit:
            continue
        before, after = cmd[:m.start(1)], cmd[m.end():]
        if hit == "ancestors":
            if _forked_neighbour(before, after):
                return (f"{m.group(1)} -A -f is piped into a loop, a {{ }} / ( ) group or a shell function (in the Bash tool grep, rg, find "
                        "and pkill are functions). That stage runs in a fork of this shell, keeps its command line and is not an ancestor, "
                        "so -A does not skip it and the result includes that fork. Anchor the pattern at the start of the target's "
                        "command line (pgrep -f '^python3 worker.py': every tool shell starts with /bin/bash -c), call the binary "
                        "(| /usr/bin/grep, | command grep), or store the result first (pids=$(pgrep -A -f ...); for p in $pids ...).")
            continue
        if m.group(1) in ("pkill", "pidwait"):
            return (f"{m.group(1)} -f: the pattern matches this command's own text, which is the command line of the shell running it, "
                    "so that shell is hit (exit 143/144). Best fix: anchor the pattern at the start of the target's command line, "
                    f"e.g. {m.group(1)} -f '^node server.js'. Every Claude Code tool shell starts with /bin/bash -c, so an anchored pattern "
                    "skips this shell, its forks and the other Bash/Monitor shells. -A (procps-ng 4.0.3+) skips only this shell's ancestors. "
                    "Or kill by PID file.")
        used = (re.search(r"(\b(if|while|until)\b|!|\$\(|`)\s*$", before)
                or re.match(r"\s*(&&|\|\||\|\s*xargs\b|>\s*/dev/null)", after)
                or re.search(r"\b(if|while|until)\b[^;]*$", before)
                or re.match(r"[^;&\n]*\|\s*(while|until|for)\b", after)  # piped into a loop that acts on each PID
                or re.search(r"(^|[^2])>\s*/dev/null", m.group(2)))  # stdout hidden = only the exit status is used
        if used:
            return ("pgrep -f: the pattern matches this command's own text, so it finds the shell running it (the wait never ends, "
                    "the kill hits the shell). Best fix: anchor the pattern at the start of the target's command line "
                    "(pgrep -f '^python3 worker.py'), which also skips other tool shells whose text names the target. "
                    "-A (procps-ng 4.0.3+) skips only this shell's ancestors, not a forked loop or another tool shell.")
    return None


def main():
    p = json.load(sys.stdin)
    if p.get("tool_name") != "Bash":
        return
    cmd = (p.get("tool_input") or {}).get("command") or ""
    if "GUARD_OK=self_kill" in cmd:
        return
    reason = check(cmd, p)
    if reason:
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": f"[self_kill] {reason} (if you really need it, put GUARD_OK=self_kill in the command and say why)"}}))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # the checker itself broke: don't block
        print(f"[guard_self_kill] checker error, passing: {e}", file=sys.stderr)
    sys.exit(0)
