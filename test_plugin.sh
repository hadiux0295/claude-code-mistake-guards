#!/bin/bash
# Usage: bash test_plugin.sh — the plugin's hook (plugin/hooks/guard_self_kill.py): commands that must be blocked are blocked, others pass.
G="$(dirname "$0")/plugin/hooks/guard_self_kill.py"
fail=0
t() {  # t <expected: block|pass> <session> <command>
  out=$(python3 -c 'import json,sys; print(json.dumps({"session_id":sys.argv[1],"transcript_path":"/home/u/.claude/projects/p/s.jsonl","tool_name":"Bash","tool_input":{"command":sys.argv[2]}}))' "$2" "$3" | python3 "$G")
  got=pass; echo "$out" | grep -q '"deny"' && got=block
  [ "$got" = "$1" ] && echo "ok    $1  $3" || { echo "FAIL  expected $1, got $got  $3"; fail=1; }
}
t block s0 'pkill -f node server.js'
t block s0 'pkill -9 -f "python worker.py"'
t pass  s0 "pkill -f '[s]erver.js'"
t pass  s0 'pkill -f "^node server.js"'
t pass  s0 'pkill node'
t pass  s0 'pkill -A -f server.js'
t pass  s0 'pkill --ignore-ancestors -f server.js'
t pass  s0 'pkill -Af server.js'
# -A skips ancestors only: a loop / group / shell function stage is a forked sibling that still matches (#93607, martin152)
t block s0 'pgrep -A -f server.js | grep -q . && echo up'
t block s0 'pgrep -A -f server.js | while read p; do kill $p; done'
t block s0 'pgrep -A -f server.js | head -1 | while read p; do echo $p; done'
t block s0 'pgrep -A -f server.js | rg server'
t block s0 'if pgrep -A -f server.js | grep -q .; then echo up; fi'
t block s0 '{ echo x; } | pgrep -A -f server.js'
t block s0 'pgrep -f server.js | while read p; do kill $p; done'
t pass  s0 'pgrep -A -f server.js | /usr/bin/grep -q . && echo up'
t pass  s0 'pgrep -A -f server.js | command grep -q . && echo up'
t pass  s0 'pgrep -A -f server.js | head -1'
t pass  s0 'pgrep -A -f server.js | xargs kill'
t pass  s0 'pids=$(pgrep -A -f server.js); for p in $pids; do kill $p; done'
t pass  s0 'while pgrep -A -f render.py >/dev/null; do sleep 1; done'
t pass  s0 "pgrep -f '^node server.js' | while read p; do kill \$p; done"
t pass  s0 "pgrep -f '^python3 worker.py' | grep -q . && echo up"
t pass  s0 "until ! pgrep -f '^bash synth_compare.sh' >/dev/null; do sleep 5; done"
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
t pass  s0 'pkill -f x  # GUARD_OK=self_kill'
t block s0 "pkill -f '[c]laude/shell-snapshots'"
t pass  s0 'pkill -f x  # GUARD_OK=self_kill'
echo '{not json' | python3 "$G"; echo "broken input -> exit $? (must be 0 = pass through)"
exit $fail
