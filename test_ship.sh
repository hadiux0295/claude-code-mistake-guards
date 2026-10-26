#!/bin/bash
# Builds one good sample product, then runs ship_check.py's self-test (inject one defect at a time, expect a failure). Needs ffmpeg + Pillow.
D="$(dirname "$0")"; G="$(mktemp -d)/good"; mkdir -p "$G"
ffmpeg -y -loglevel error -f lavfi -i "testsrc=s=320x240:d=3" "$G/preview.mp4"
python3 - "$G" <<'P'
import json, sys; from PIL import Image
g = sys.argv[1]
Image.new("RGB", (64, 64), (200, 120, 40)).save(f"{g}/cover.png")
json.dump({"title": "Cozy Cabin Party Game", "description": "Printable game for 6-10 players.",
           "tags": ["party game", "printable", "cabin mystery"],
           "files": [{"path": "preview.mp4", "tool": "my render script"}, {"path": "cover.png", "tool": "image tool A"}]},
          open(f"{g}/listing.json", "w"))
P
python3 "$D/tools/ship_check.py" "$G" && python3 "$D/tools/ship_check.py" --selftest "$G"
