#!/bin/bash
# Usage: bash test_guard_bash.sh — commands that must be blocked are blocked, and commands that must pass pass.
G="$(dirname "$0")/hooks/guard_bash.py"
export GUARD_UPLOAD_ROOT="$(mktemp -d)" CLAUDE_PROJECT_DIR="$(mktemp -d)"
mkdir -p "$GUARD_UPLOAD_ROOT/handoff" && touch "$GUARD_UPLOAD_ROOT/handoff/cover.png"
fail=0
t() {  # t <expected: block|pass> <session> <command>
  out=$(python3 -c 'import json,sys; print(json.dumps({"session_id":sys.argv[1],"tool_name":"Bash","tool_input":{"command":sys.argv[2]}}))' "$2" "$3" | python3 "$G")
  got=pass; echo "$out" | grep -q '"deny"' && got=block
  [ "$got" = "$1" ] && echo "ok    $1  $3" || { echo "FAIL  expected $1, got $got  $3"; fail=1; }
}
t block s1 'pkill -f node server.js'
t block s1 'while pgrep -f render.py >/dev/null; do sleep 1; done'
t pass  s1 'while pgrep -f "[r]ender.py" >/dev/null; do sleep 1; done'
t pass  s1 'pgrep -f render.py'
t block s1 'cd ~/proj && git pull --rebase'
t pass  s1 'bash scripts/safe_pull.sh'
t block s1 'curl -s https://www.example-market.com/shop/x'
t pass  s1 'curl -s https://api.example-market.com/v3/listings'
t pass  s1 'curl -s https://example.org/'
t block s1 "cp a.png $GUARD_UPLOAD_ROOT/a.png"
t block s1 "mkdir -p $GUARD_UPLOAD_ROOT/try_1025"
t block s1 "cp new/cover.png $GUARD_UPLOAD_ROOT/handoff/upload_1025/"
t pass  s1 "cp new/cover.png $GUARD_UPLOAD_ROOT/handoff/_old_1025/"
t pass  s1 "cp new/other.png $GUARD_UPLOAD_ROOT/handoff/upload_1025/"
t block s1 'pkill -f x  # GUARD_OK=bare_pull'
t pass  s1 'pkill -f x  # GUARD_OK=self_kill'
t block s2 'git commit -m "fix: typo"'
t pass  s2 'git commit -m "fix: typo
said: today first = 2 releases"'
t pass  s2 'git commit -m "second commit"'
echo '{not json' | python3 "$G"; echo "broken input -> exit $? (must be 0 = pass through)"
exit $fail
