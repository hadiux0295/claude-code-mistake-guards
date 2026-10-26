#!/bin/bash
# Usage: bash test_gen.sh — gen_gate, add_unique and baseline_check exit with the expected codes.
D="$(dirname "$0")"; W="$(mktemp -d)"; fail=0
ex() { [ "$2" = "$1" ] && echo "ok    exit $2  $3" || { echo "FAIL  expected exit $1, got $2  $3"; fail=1; }; }
cat > "$W/rows.json" <<'J'
[{"id":"c1","kind":"story","airport":"ICN","year":1998,"source":"x"},
 {"id":"c2","kind":"story","airport":"ICN","year":2005,"source":"x"},
 {"id":"tile1","kind":"tile","base_image":""},
 {"id":"c3","kind":"story","airport":"GMP","year":1990}]
J
python3 "$D/tools/gen_gate.py" "$W/rows.json"; ex 2 $? "fallback present -> stop"
python3 "$D/tools/gen_gate.py" "$W/rows.json" --allow-fallback >/dev/null; ex 0 $? "allowed -> pass"
python3 "$D/tools/add_unique.py" "$W/r.jsonl" "PDF upload failed" "a" >/dev/null; ex 0 $? "new record"
python3 "$D/tools/add_unique.py" "$W/r.jsonl" "PDF  upload failed!" "b" 2>/dev/null; ex 1 $? "same normalized title -> blocked"
python3 "$D/tools/add_unique.py" "$W/r.jsonl" "PDF upload failed again" "c"; ex 0 $? "similar -> warning only"
python3 - "$W" <<'P'
import sys; from PIL import Image
w=sys.argv[1]
m=Image.new("L",(100,100),0); [m.putpixel((x,y),255) for x in range(100) for y in range(60,100)]; m.save(f"{w}/mask.png")
p=Image.new("RGBA",(30,30),(0,0,0,0)); [p.putpixel((x,y),(200,50,50,255)) for x in range(10,20) for y in range(5,20)]; p.save(f"{w}/prop.png")
P
python3 "$D/tools/baseline_check.py" "$W/mask.png" "$W/prop.png" 40 40; ex 0 $? "feet on the ground (y=40+19+1=60)"
python3 "$D/tools/baseline_check.py" "$W/mask.png" "$W/prop.png" 40 30; ex 1 $? "floating prop a canvas-bottom check would miss"
exit $fail
