#!/usr/bin/env python3
"""Pre-ship check. Run it on one product folder right before uploading; if anything fails it stops with exit 1.

Product folder = listing.json + files. listing.json example:
  {"title": "...", "description": "...", "tags": ["..."],
   "files": [{"path": "preview.mp4", "tool": "my render script"}, {"path": "cover.png", "tool": "image tool A"}]}

One check = one defect that actually shipped. It turns a checklist sentence ("all tags are 20 chars or less") into code.
Banned-word and trademark checks live here, not inside a generator: every product passes this step, whichever generator made it.
  python3 ship_check.py <product folder>...                check
  python3 ship_check.py --selftest <good product folder>   copy the folder, inject one defect at a time, confirm the check really fails
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

TAG_MAX = 20                                   # the marketplace's tag length limit
REQUIRED = [r"\.mp4$"]                         # files every product must have (e.g. a preview video)
BANNED = [r"\bdisney\b", r"\bpokemon\b", r"\blego\b"]  # words never allowed in title / tags / description (trademarks etc.)
COMMERCIAL_OK = {"my render script", "image tool A"}  # tools whose terms (incl. beta / preview clauses) you checked allow selling the output
BLACK_MIN_SEC = 0.5                            # fail if a fully black stretch lasts longer than this


def black_spans(video):
    """Find fully black stretches with ffmpeg blackdetect. Without ffmpeg the check cannot run, so it counts as a failure."""
    if not shutil.which("ffmpeg"):
        return ["ffmpeg missing — cannot run the black-frame check"]
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", video, "-vf",
                        f"blackdetect=d={BLACK_MIN_SEC}:pix_th=0.10", "-an", "-f", "null", "-"],
                       capture_output=True, text=True)
    return [f"black screen {m.group(1)}s-{m.group(2)}s" for m in
            re.finditer(r"black_start:([\d.]+) black_end:([\d.]+)", r.stderr)]


def check(folder):
    errs = []
    try:
        meta = json.load(open(os.path.join(folder, "listing.json"), encoding="utf-8"))
    except Exception as e:
        return [f"cannot read listing.json: {e}"]
    for t in meta.get("tags", []):
        if len(t) > TAG_MAX:
            errs.append(f"tag {len(t)} chars > {TAG_MAX}: {t!r}")
    text = " ".join([meta.get("title", ""), meta.get("description", "")] + meta.get("tags", []))
    errs += [f"banned word: {m.group(0)!r}" for pat in BANNED for m in [re.search(pat, text, re.I)] if m]
    files = meta.get("files", [])
    for pat in REQUIRED:
        if not any(re.search(pat, f.get("path", ""), re.I) for f in files):
            errs.append(f"required file missing: {pat}")
    for f in files:
        path = os.path.join(folder, f.get("path", ""))
        if not os.path.isfile(path):
            errs.append(f"listed but not on disk: {f.get('path')}")
            continue
        if f.get("tool") not in COMMERCIAL_OK:
            errs.append(f"source tool not on the commercial-OK list: {f.get('path')} <- {f.get('tool')!r}")
        if path.lower().endswith(".mp4"):
            errs += [f"{f['path']}: {s}" for s in black_spans(path)]
    return errs


DEFECTS = {  # name → function that injects one defect into a good product. Each one must make the check fail.
    "long tag": lambda m, d: m["tags"].append("x" * (TAG_MAX + 1)),
    "banned word": lambda m, d: m.__setitem__("title", m["title"] + " Lego"),
    "video missing": lambda m, d: m.__setitem__("files", [f for f in m["files"] if not f["path"].endswith(".mp4")]),
    "unverified source tool": lambda m, d: m["files"][0].__setitem__("tool", "beta generation feature"),
    "black screen": lambda m, d: subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "color=black:s=320x240:d=2",
         os.path.join(d, [f["path"] for f in m["files"] if f["path"].endswith(".mp4")][0])], check=True),
}


def selftest(good):
    ok = True
    base = check(good)
    print(("ok    good product passes" if not base else f"FAIL  the good product already fails: {base}"))
    ok &= not base
    for name, inject in DEFECTS.items():
        d = tempfile.mkdtemp()
        shutil.copytree(good, d, dirs_exist_ok=True)
        m = json.load(open(os.path.join(d, "listing.json"), encoding="utf-8"))
        inject(m, d)
        json.dump(m, open(os.path.join(d, "listing.json"), "w", encoding="utf-8"))
        errs = check(d)
        print(f"ok    {name} -> caught ({errs[0]})" if errs else f"FAIL  injected {name} but it passed")
        ok &= bool(errs)
        shutil.rmtree(d)
    return ok


if __name__ == "__main__":
    if sys.argv[1:2] == ["--selftest"]:
        sys.exit(0 if selftest(sys.argv[2]) else 1)
    bad = 0
    for folder in sys.argv[1:]:
        errs = check(folder)
        print(f"{'FAIL' if errs else 'PASS'}  {folder}")
        for e in errs:
            print(f"      - {e}")
        bad += bool(errs)
    sys.exit(1 if bad or not sys.argv[1:] else 0)
