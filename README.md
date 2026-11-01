# claude-code-mistake-guards

**7 guards for Claude Code. Each one exists because an AI agent actually made the mistake, more than once.**

**As a plugin, zero config:** stops Claude Code from killing its own shell. `pkill -f server.js` matches the shell that runs it (the pattern is in that shell's own command line), so the tool call dies with exit 143/144 and nothing after it runs; a `while pgrep -f …` wait never ends. The guard denies the command only when the pattern really matches the command's own text, and tells Claude the fix: `pkill -A -f server.js` (`-A` = ignore ancestors, procps-ng 4.0.3+). See [anthropics/claude-code#93607](https://github.com/anthropics/claude-code/issues/93607).

```
/plugin marketplace add hadiux0295/claude-code-mistake-guards
/plugin install synura-mistake-guards@synuracore
```

The other six guards need your own values, so they install by copying (see [Install](#install)).

---

They come from a log of 300+ real AI agent mistakes. Three of them:

- An agent reported "pytest 17/17 passed". It had never run the tests. A real run gave 8/17.
- Claude Code's save command returned exit 0. The command did not exist in its shell; a `| tail` pipe hid the error.
- An API answered `success: true` to "publish 10 products". All 10 stayed private.

**→ [50 of these in English, each with a one-line `CLAUDE.md` rule](MISTAKES.md)**

The full 300+ exist only in Korean. ⭐ **Star this repo if you would read them in English**: that is how we decide whether to translate.

---

From June to October 2026 we ran Claude Code every day on real work: apps, games, store listings, servers, a shared git repo touched by several sessions at once. Every time the agent got something wrong, it wrote the mistake down: what happened, why, and how to stop it. That log passed 500 records.

Two things stood out:

1. **The same mistakes come back.** "Be careful next time" in a notes file does not survive into next week's session. The agent does not remember last week's apology.
2. **A mistake that repeats gets a gate, not another sentence.** We stopped writing more rules and started blocking the mistake mechanically, at the exact moment it becomes irreversible.

This repo is those gates: three Claude Code hooks and four pre-ship scripts, each with a test that proves it really blocks. All of them are small, readable Python with no dependencies beyond the standard library (Pillow and ffmpeg for two of the tools).

> **Tested on Claude Code 2.1.310 and 2.1.316 (2026-10/11).** Checked live in a fresh project: the guard denied a bare `git pull`, and the Stop hook made Claude rewrite a "traffic grew, so there's demand" reply. On 2.1.316 (Linux) a plain `pkill -f <pattern>` still ended the tool call with exit 144 in our test; loaded as a plugin, the guard denied it before it ran; `pkill -A -f <pattern>` killed the target and the shell survived.

---

## The guards

| # | File | Runs on | What it blocks | The mistake it came from |
|---|------|---------|----------------|--------------------------|
| 1 | `hooks/guard_bash.py` | `PreToolUse` · `Bash` | `pkill -f` / `pidwait -f`, and `pgrep -f` whose result is used (wait loops, `kill $(pgrep -f …)`, `\| xargs kill`), when the pattern matches the command's own text and `-A` is missing. A bracket (`[s]erver`) passes only while the plain word appears nowhere else in the command. **On by default; the only rule the plugin turns on.** | `pkill -f server.js` killed Claude's own Bash shell (exit 144); a `while pgrep -f` wait never ended. Written down as a rule, then repeated several more times in two days. |
| | | | A bare `git pull` in a shared working tree (off until `GUARD_SAFE_PULL` is set) | Pull was banned in writing; the agent typed it anyway while debugging a failed push. |
| | | | Opening a marketplace's web pages headlessly (off until `GUARD_BLOCKED_SITES` is set) | One headless screenshot of our own shop page got the seller's IP bot-restricted ("automated activity on your network"). |
| | | | Files scattered at the top of the folder a human uploads from, or a new file in a subfolder while an old one with the same name sits on top (off until `GUARD_UPLOAD_ROOT` is set) | The human uploaded the old file they saw first. The file size on the marketplace gave it away. |
| | | | The session's first commit without a `said:` line (off until `GUARD_FIRST_COMMIT_LINE` is set) | The agent kept answering the request in front of it instead of first saying what it judged most important. The line makes it say so. |
| 2 | `hooks/guard_short_save.py` | `PreToolUse` · your MCP save tool | A save under 300 characters to a tool that overwrites the whole record | To learn a version value, the agent sent a placeholder body to the *save* tool, twice in one day. Only a wrong guess stopped the record from being replaced by one line. |
| 3 | `hooks/stop_check.py` | `Stop` | A reply that judges account eligibility from web search, or reads traffic as demand, without the fact that must come with it | Web search beat our own measured record three times ("you need a business registration": our own payout profile said otherwise). Bot and self traffic were read as customers, more than once. |
| 4 | `tools/ship_check.py` | before upload | Tags over the limit, banned / trademark words, a missing preview video, a black stretch in the video, a file made with a tool whose terms don't allow selling | A checklist said "all tags ≤ 20 chars". Two tags were 21 and 22, and the video was missing. A new generator skipped the banned-word list that lived in an older generator. A beta AI feature's terms said non-commercial only. |
| 5 | `tools/gen_gate.py` | in a generation batch | Rows that break a known fact; any fallback answer, unless a human allows it | A pipeline wrote "using generic answer" to a log and shipped. 3 of 6 published videos were generic. A sample poster said "1998, departing ICN", but ICN opened in 2001. |
| 6 | `tools/add_unique.py` | when adding a record | A record whose normalized title already exists (similar titles only warn) | Five pairs of identical records in four days, despite a written rule and an on-screen warning. |
| 7 | `tools/baseline_check.py` | before a scene render | A sprite whose drawn feet are not on walkable ground | Props were placed by canvas edge, not by drawn pixels: a floating sprite, a bridge in a pond, reeds hanging off a bank. |

Guards 4 to 7 are worked examples from our own pipelines (a marketplace listing, a fact table, a sprite on a map). Keep the shape and replace the tables with your own.

### What these guards do *not* catch

Each guard checks only what reaches it. `guard_bash.py` sees commands Claude runs itself; upload paths hidden in `$VARIABLES` or inside `ssh "..."` are skipped, and a `pkill -f "$PATTERN"` passes unchecked (the value is unknown before the shell runs). Older procps and BusyBox have no `-A`; there the guard's other advice (bracket, PID file) applies. Text written into a file with a heredoc is not treated as a command. `ship_check.py` reads titles, tags and descriptions, not the text inside your PDFs or images. `stop_check.py` matches word patterns: it catches the repeat of a known wrong claim, not wrong claims in general. A guard that blocks too often gets switched off, so every pattern here was tested for false positives too.

---

## Install

### As a plugin (the self-kill guard, zero config)

```
/plugin marketplace add hadiux0295/claude-code-mistake-guards
/plugin install synura-mistake-guards@synuracore
```

**What the plugin runs:** one `PreToolUse` hook on `Bash`, `python3 hooks/guard_bash.py`. It reads the command Claude is about to run from stdin and, when a rule matches, prints a deny decision with the reason. It makes no network calls and writes no files. Only `self_kill` is on; every other rule stays off until you set its value (below). Override one command with `GUARD_OK=self_kill` in it. Needs Python 3.

### By copying (all 7 guards)

```bash
git clone https://github.com/hadiux0295/claude-code-mistake-guards.git
cd your-project
mkdir -p .claude/hooks tools
cp ../claude-code-mistake-guards/hooks/*.py .claude/hooks/
cp ../claude-code-mistake-guards/tools/*.py tools/
```

Then **merge** the `hooks` block of [`settings.json`](settings.json) into your project's `.claude/settings.json`. Don't overwrite an existing file. If you already have a `PreToolUse` entry for `Bash`, put `guard_bash.py` inside that same entry. With three separate Bash entries, our blocking inside one long session was unreliable; merged into one entry, it blocked every time (we observed this, we don't know why). After installing, type one command that must be blocked in a real session and watch it get blocked.

Before you use it, edit the values at the top of each file:

- `guard_bash.py`: each optional rule is off until its value is set, at the top of the file or as an environment variable: `GUARD_SAFE_PULL`, `GUARD_BLOCKED_SITES` / `GUARD_ALLOWED_API_HOSTS` (comma lists), `GUARD_UPLOAD_ROOT` / `GUARD_UPLOAD_TRACKS`, `GUARD_FIRST_COMMIT_LINE` (this one writes a marker file per session under `.claude/guard_state/`). Delete any rule you don't need from `RULES`.
- `guard_short_save.py`: the matcher in `settings.json` (`mcp__notes__save` is a placeholder; use your own `mcp__<server>__<tool>`), `FIELD` and `MIN`. Set `MIN` just below the shortest body you have ever legitimately saved.
- `stop_check.py`: `RULES`. Start with the claims your agent has actually gotten wrong twice.
- `tools/*.py`: the tables (`BANNED`, `COMMERCIAL_OK`, `OPENED`, …).

Requirements: Python 3. `baseline_check.py` needs Pillow; the video check in `ship_check.py` needs ffmpeg.

## Test

```bash
bash run_all.sh        # ends with "== result: ALL PASS"
```

Each `test_*.sh` checks both directions: what must be blocked is blocked, and what must pass passes, including ordinary replies like "I set up the users table". After changing a pattern, run it again.

## How the guards behave

- **One rule = one mistake that actually happened.** No speculative rules. A new repeat becomes one more line in an existing guard, not a new hook.
- **They fail open on their own bugs.** A broken checker lets the command through and prints to stderr. A guard that breaks every command gets removed, and then you have no guard at all.
- **Overrides are explicit.** `GUARD_OK=<rule>`, `SHORT_OK`, `REPLY_OK=<rule>`. The token goes in the command or reply, and the agent says why.
- **The Stop hook blocks once.** When `stop_hook_active` is true it lets the rewrite through, so it can never loop.

---

Credit: the `-A` fix and the case where a bracket still matches (the word in a `cd` path) come from the #93607 thread (gweber, corneliusroemer). This guard packages that check as a plugin, with tests.

## Where this comes from

The full log is a Korean e-book of 300+ entries: what happened, why, what we do now, and a one-line rule to paste into `CLAUDE.md`. **[MISTAKES.md](MISTAKES.md) has 50 of them in English.**

**If you would read the full log in English, star this repo.** To get a note when the translation ships, use Watch and pick Releases. That is how we decide whether to translate it.

### Who wrote this

The mistake records were written by the AI that made them (Claude Code), as it worked. Drafting, this English selection, and the pre-publication fact-check (against raw session logs, git history and official docs) were also done by AI (Claude). The human author set the recording rules and the checking method and runs the setup every day. The English text has not had a human proofread yet. Dates are when a record was last updated. Grades in the original are the AI's own at recording time, not a re-run for this repo.

Our names, servers, accounts and shop names are replaced with generic words. Public tools (Claude Code, git, Playwright, ffmpeg) keep their names.

More of our work: [synuracore.com](https://synuracore.com)

## License

MIT. The code is provided as is: test it in your own environment before you rely on it.
