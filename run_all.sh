#!/bin/bash
# Runs every guard test. Exits 1 if any result differs from what is expected.
D="$(cd "$(dirname "$0")" && pwd)"; bad=0
for t in test_guard_bash.sh test_plugin.sh test_save_stop.sh test_ship.sh test_gen.sh; do
  echo "== $t"; bash "$D/$t" || bad=1
done
echo "== result: $([ $bad = 0 ] && echo 'ALL PASS' || echo 'FAILURES')"; exit $bad
