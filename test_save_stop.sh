#!/bin/bash
# Usage: bash test_save_stop.sh — short-save guard and reply check block / pass as expected.
H="$(dirname "$0")/hooks"; fail=0
j() { python3 -c 'import json,sys; print(json.dumps(json.loads(sys.argv[1])))' "$1"; }
t() {  # t <expected block|pass> <script> <json>
  out=$(j "$3" | python3 "$H/$2"); got=pass; echo "$out" | grep -q '"deny"\|"block"' && got=block
  [ "$got" = "$1" ] && echo "ok    $1  $2  ${3:0:90}" || { echo "FAIL  expected $1, got $got  $3"; fail=1; }
}
LONG=$(python3 -c 'print("x"*320)')
t block guard_short_save.py '{"tool_name":"mcp__notes__save","tool_input":{"key":"k","content":"probe"}}'
t pass  guard_short_save.py "{\"tool_name\":\"mcp__notes__save\",\"tool_input\":{\"key\":\"k\",\"content\":\"$LONG\"}}"
t pass  guard_short_save.py '{"tool_name":"mcp__notes__save","tool_input":{"key":"k","content":"short note SHORT_OK: list label only"}}'
t block stop_check.py '{"stop_hook_active":false,"last_assistant_message":"Several blog posts and search results say accounts from your country cannot sign up. Use another marketplace."}'
t pass  stop_check.py '{"stop_hook_active":false,"last_assistant_message":"Search results say accounts from your country cannot sign up, but our own record (measured in October) shows the sign-up worked."}'
t pass  stop_check.py '{"stop_hook_active":true,"last_assistant_message":"Several blog posts and search results say accounts from your country cannot sign up."}'
t block stop_check.py '{"stop_hook_active":false,"last_assistant_message":"Traffic grew 40% this week. That is a demand signal."}'
t pass  stop_check.py '{"stop_hook_active":false,"last_assistant_message":"Traffic grew 40% this week, but the user agents show half of it was bots."}'
t pass  stop_check.py '{"stop_hook_active":false,"last_assistant_message":"The build finished. All 12 tests pass."}'
t pass  stop_check.py '{"stop_hook_active":false,"last_assistant_message":"I searched the codebase for the account model and fixed the signup handler."}'
t pass  stop_check.py '{"stop_hook_active":false,"last_assistant_message":"I set up the users table and moved the views into one folder. All tests pass."}'
echo '{}' | python3 "$H/stop_check.py"; echo "empty input -> exit $?"
exit $fail
