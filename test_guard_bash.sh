#!/bin/bash
# Usage: bash test_guard_bash.sh — commands that must be blocked are blocked, and commands that must pass pass.
G="$(dirname "$0")/hooks/guard_bash.py"
fail=0
t() {  # t <expected: block|pass> <session> <command>
  out=$(python3 -c 'import json,sys; print(json.dumps({"session_id":sys.argv[1],"tool_name":"Bash","tool_input":{"command":sys.argv[2]}}))' "$2" "$3" | python3 "$G")
  got=pass; echo "$out" | grep -q '"deny"' && got=block
  [ "$got" = "$1" ] && echo "ok    $1  $3" || { echo "FAIL  expected $1, got $got  $3"; fail=1; }
}

echo "== out of the box (plugin install): only self_kill is on"
export CLAUDE_PROJECT_DIR="$(mktemp -d)"
t block s0 'pkill -f node server.js'
t block s0 'pkill -9 -f "python worker.py"'
t pass  s0 "pkill -f '[s]erver.js'"
t pass  s0 'pkill -f "^node server.js"'
t pass  s0 'pkill node'
t pass  s0 'pkill -A -f server.js'
t pass  s0 'pkill --ignore-ancestors -f server.js'
t pass  s0 'pkill -Af server.js'
t block s0 "cd /srv/server && pkill -f '[s]erver'"
t block s0 "pkill -f '[s]erver.js'; echo server.js stopped"
t pass  s0 'pkill -f "$PATTERN"'
t block s0 "pkill -f '[b]ash'"
t block s0 "pkill -f '[s]hell-snapshots'"
t block s0 'pidwait -f render.py'
t block s0 'while pgrep -f render.py >/dev/null; do sleep 1; done'
t block s0 'until ! pgrep -f render.py; do sleep 1; done'
t block s0 'kill $(pgrep -f server.js)'
t block s0 'pgrep -f server.js | xargs kill'
t block s0 'pgrep -f server.js >/dev/null && echo up'
t pass  s0 'while pgrep -f "[r]ender.py" >/dev/null; do sleep 1; done'
t pass  s0 'kill $(pgrep -f "[s]erver.js")'
t pass  s0 'pgrep -af render.py'
t pass  s0 'pgrep -af "render|node" 2>/dev/null'
t pass  s0 'echo "never run pkill -f here" > notes.txt'
t pass  s0 'grep -n pkill notes.md'
t pass  s0 "cat > notes.md <<'EOF'
pkill -f server.js kills the shell
EOF"
t block s0 "bash <<'EOF'
pkill -f server.js
EOF"
t block s0 "bash -c 'pkill -f server.js'"
t block s0 "ssh box 'pkill -f server.js'"
t block s0 'sudo pkill -f server.js'
t pass  s0 'cd ~/proj && git pull --rebase'
t pass  s0 'curl -s https://www.example-market.com/shop/x'
t pass  s0 "cp a.png $HOME/Uploads/a.png"
t pass  s0 'git commit -m "fix: typo"'
[ -e "$CLAUDE_PROJECT_DIR/.claude" ] && { echo "FAIL  wrote $CLAUDE_PROJECT_DIR/.claude with every optional rule off"; fail=1; } || echo "ok    no files written"
t block s0 'pkill -f x  # GUARD_OK=bare_pull'
t pass  s0 'pkill -f x  # GUARD_OK=self_kill'

echo "== configured: every rule on"
export GUARD_SAFE_PULL=scripts/safe_pull.sh GUARD_BLOCKED_SITES=example-market.com GUARD_ALLOWED_API_HOSTS=api.example-market.com
export GUARD_FIRST_COMMIT_LINE="said:" GUARD_UPLOAD_ROOT="$(mktemp -d)" CLAUDE_PROJECT_DIR="$(mktemp -d)"
mkdir -p "$GUARD_UPLOAD_ROOT/handoff" && touch "$GUARD_UPLOAD_ROOT/handoff/cover.png"
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
t block s2 'git commit -m "fix: typo"'
t pass  s2 'git commit -m "fix: typo
said: today first = 2 releases"'
t pass  s2 'git commit -m "second commit"'
echo '{not json' | python3 "$G"; echo "broken input -> exit $? (must be 0 = pass through)"
exit $fail
