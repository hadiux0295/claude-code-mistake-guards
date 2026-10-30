# 50 real Claude Code mistakes, and the rule that stops each

Every entry below happened in our own daily work with Claude Code and other AI agents between June and October 2026. Each one has what happened, why, and a one-line rule you can paste into your `CLAUDE.md`. Entries marked **🛡 now blocked by a guard** have a mechanical check in this repo or in our setup, because the written rule alone did not stop the repeat.

The tag under each entry is the original record number and the month it was last updated. These are 50 of 300+ entries; the full log exists in Korean. See [README](README.md) for how the records were written and checked.

**Contents**
1. ["Done!" that wasn't: success signals that lie](#1-done-that-wasnt-success-signals-that-lie)
2. [Answering from memory](#2-answering-from-memory)
3. [Reading numbers backwards](#3-reading-numbers-backwards)
4. [One keystroke from irreversible](#4-one-keystroke-from-irreversible)
5. [One repo, many hands: parallel sessions and git](#5-one-repo-many-hands-parallel-sessions-and-git)
6. [Works on my machine](#6-works-on-my-machine)
7. [What someone else's API told us](#7-what-someone-elses-api-told-us)
8. [Who ends up reading it](#8-who-ends-up-reading-it)
9. [The harness and the shell](#9-the-harness-and-the-shell)
10. [Notes that drift](#10-notes-that-drift)

---

## 1. "Done!" that wasn't: success signals that lie

Exit 0, `success: true`, HTTP 200 and "passed" usually mean *the request was accepted* or *the format is right*. Whether the result actually exists has to be read back another way. The agent will not make that distinction for you.

### 1. "17/17 passed" without running the tests
An autonomous agent on a free open model was asked to write and run tests. Two minutes later: "pytest 17/17 passed (100%)". A real run gave 8/17: two missing dependencies, six interface mismatches, one logic bug. The agent had no shell access, so it wrote what pytest output *looks like*. A language model writes a plausible next sentence; it does not mark whether that sentence is a real execution result.

> **CLAUDE.md:** When reporting test results, paste the command you ran and the last line of its output (pass/fail counts). If you did not run it, write "not run".

<sub>record #0036 · 2026-06</sub>

### 2. Exit 0 for a command that doesn't exist
Claude Code ran our wrap-up save command (a shell function). Result: exit 0. Nothing was saved; the first line of output said `command not found`. Two things stacked. Claude Code's Bash tool runs a non-interactive shell, and Ubuntu's default `.bashrc` returns early for non-interactive shells, so functions defined below that line never exist. And we had piped the output into `| tail`, so the exit code was `tail`'s.

> **CLAUDE.md:** When you cut output with a pipe, put `set -o pipefail` first. If the output contains "not found" or "error", report failure even when the exit code is 0.

<sub>record #0766 · 2026-09</sub>

### 3. `success: true`, and the products stayed private
We set 10 products to "published" through a digital-goods platform's REST API. Every response was `{success: true}`, and the agent reported "10 published". On the shop page, all 10 were still private. The API accepted the field but did not apply it (as of 2026-09); the only publish path we found was the official CLI. A success response means "request received", not "state changed".

> **CLAUDE.md:** After writing to an external service, report "done" based on the real state read back from the public URL or a read API, not on the response's success flag.

<sub>record #0484 · 2026-09</sub>

### 4. Started a new server, and the old one answered
To review game graphics we started `python -m http.server` and took screenshots. Old art showed up, although the files on disk were new. A server from an earlier session still held the port; the new one died on `Address already in use`, but we had sent stderr to `/dev/null` too. The server that answered was serving a different folder.

> **CLAUDE.md:** After starting a server for review, fetch one file with curl and check its hash matches the file on disk before going on.

<sub>record #0080 · 2026-07</sub>

### 5. Every URL returned 200: a check that couldn't fail
A curl loop checked that login-protected pages were alive. All 200. One of them was really a 404. Without a valid session, every URL returned the login screen with a 200, and the curl version in use did not keep the Secure cookie it got over `http://localhost`. The loop only ever confirmed "the login page loads".

> **CLAUDE.md:** When you write a check script, run it on one input that must fail, and show that it can fail, before trusting it.

<sub>record #0822 · 2026-09</sub>

### 6. A warning in the log, and the pipeline shipped anyway 🛡
When a video pipeline lacked source material it substituted a generic answer and logged one line. Three of six published videos went out that way, and the weakest performers were among them. Nobody reads batch logs. Now the pipeline stops with exit 2 on any fallback and continues only with `--allow-fallback` (see `tools/gen_gate.py`).

> **CLAUDE.md:** When a quality warning appears (fallback, missing item, substitution), don't just log it: stop and report to me.

<sub>record #0109 · 2026-07 · 🛡 now blocked by a guard</sub>

### 7. "Batch complete", half the output missing
A batch generated animations for several game characters and printed "animations complete". One character would have shipped with no attack or death animation. A try/except around each *character* caught one animation's timeout and silently skipped that character's remaining animations. The loop finished normally. Only comparing PNG counts per character against the expected counts showed it.

> **CLAUDE.md:** Report a batch as done with a table of produced count vs expected count, not because the loop ended.

<sub>record #0646 · 2026-09</sub>

### 8. A quiet monitor looks exactly like a missing monitor
We wrote a script to check that our "silent when healthy" monitors were still alive. Its first version made the very mistake it was meant to catch: it judged health from an empty log. An empty log means "fine" or "deleted / never ran", and you cannot tell which. It would report "healthy" for a monitor that no longer existed.

> **CLAUDE.md:** Jobs that are silent when healthy must write their last-run time on every run; judge liveness from that timestamp, not from log content.

<sub>record #0643 · 2026-09</sub>

### 9. "All tags ≤ 20 characters": a lie in the checklist 🛡
An upload kit handed to a human said "all tags 20 chars or less". Two tags were 21 and 22, and the product video was missing. The human found both in the store editor. Two days later two more kits went out without video. The checklist line was what the agent believed it had checked, not a measurement. Now `tools/ship_check.py` measures the tags and fails a kit with no video.

> **CLAUDE.md:** Before writing "all X ≤ N" or "all present" in a checklist, attach the command that counted it and its output. If you didn't count, don't write the line.

<sub>record #1187 · #1219 · 2026-10 · 🛡 now blocked by a guard</sub>

---

## 2. Answering from memory

### 10. A remembered flag, a remembered model name
An automation script passed `--output-format json` to an agent CLI that has no such flag. It died with `unknown flag`, again and again until someone looked. Model names are the same trap: a remembered model name can 404 quietly or fall back to another model with a different price. Similar tools have similar flags, and the model mixes them up.

> **CLAUDE.md:** Never write CLI flags or model names from memory. Use only values confirmed in `--help` output or the official model list, and show the command you checked with.

<sub>record #0001 · #0187 · 2026-08</sub>

### 11. A price quoted from memory, off by about 3×
We asked for help buying an NVMe SSD. The agent quoted a price for 1 TB and built a whole recommendation (512 GB vs 1 TB, which brand) on it. On a price comparison site the 512 GB drive alone cost more than that, and 1 TB was close to three times. Memory prices had jumped that year. The model remembers training-time prices.

> **CLAUDE.md:** Never state prices or fees from memory. Before purchase or plan advice, fetch the current price page and cite source and date.

<sub>record #0842 · 2026-09</sub>

### 12. "That's on the banned list." It wasn't.
A "new hero skill" was proposed for our game. The agent held it back, citing the design doc's list of forbidden things. Reading all 14 items later: no "no new skills" item. The two real constraints ("don't add input methods", "one new system only") didn't block it, and it was adopted. The agent remembered a mood ("this project is strict about features") and quoted it as a rule.

> **CLAUDE.md:** When you block a proposal on a rule, open the source and quote the item number and sentence. If there's no item to quote, don't block.

<sub>record #0403 · 2026-09</sub>

### 13. Judged a policy from a search summary; the original said otherwise
Twice. YouTube's AI-disclosure rule: blogs said background music is exempt, but the official help page lists "AI generated music" among its examples (its requirement sentence is narrower, so we chose to disclose). Two months later, a handmade marketplace's ban on AI-made instruction manuals: the search summary dropped the last sentence that extended the ban to product components. Secondary sources often drop the one clause that matters.

> **CLAUDE.md:** When judging a platform policy, quote the exact sentence from the official original. If you can't open the original, don't judge: write "needs original text".

<sub>record #0317 · #1275 · 2026-10</sub>

### 14. Web search beat our own measured record, three times 🛡
Web search said a business registration was required for paid apps in our country; a 90-day plan was built on it. Our own payment profile, opened directly, was already verified as "individual", and our notes said so weeks earlier. Then twice more, about a social platform's business account. Ten blogs agreeing is still weaker than one record of our own account. Now a Stop hook catches this claim (`hooks/stop_check.py`).

> **CLAUDE.md:** Before stating account eligibility, region limits or platform conditions, search the project records first. If web results disagree with our measured record, follow the record and report the difference.

<sub>record #0258 · #0679 · #1266 · 2026-10 · 🛡 now blocked by a guard</sub>

### 15. A plausible cause, and the real one was a dead key
Speech recognition returned empty results. The agent reported "audio format problem (sample rate / channels)". The real cause was an expired API key: auth failed with 401, and our code received the cancel event and did nothing with it, so it looked like "recognized nothing". A few seconds of checking would have settled it.

> **CLAUDE.md:** When reporting a failure cause, attach the output that confirmed it. Otherwise write "guess", and run the cheapest checks first (key, permissions, network).

<sub>record #0658 · 2026-09</sub>

### 16. An empty result read as "doesn't exist"
A note server returned 404 for a note ID, and the agent declared it "deleted"; a report was skipped and "data loss" was recorded. That server has no get-by-ID at all; every ID returns 404. The note was alive in another collection. Separately, a two-word search returned `[]` and the agent said "not recorded"; the tool matched the whole string against stored keywords. 404 and `[]` can mean "can't ask that".

> **CLAUDE.md:** Don't report "missing / deleted" from a 404 or empty search alone. Look through the full list, or first run the same query on something you know exists.

<sub>record #0690 · #0693 · 2026-09</sub>

---

## 3. Reading numbers backwards

### 17. "Zero purchases": there was no ruler
GA4 showed no purchase events, and "0 purchases" was about to become the conclusion. The code had exactly one instrumented event: `app_open`. A second case: a single line, `if(!isNative) return`, meant no web traffic tag had ever been sent. An uninstrumented metric and a true zero look identical on a dashboard.

> **CLAUDE.md:** Before writing "none" for a zero metric, find the code that sends the event and trigger it once yourself. If there's no instrumentation, write "not measured", not 0.

<sub>record #0172 · #0562 · 2026-09</sub>

### 18. 403, missing from search, 400: ask a known-good target first
A list call returned `403 INSUFFICIENT_SCOPE`, and the agent blamed the API key; the same call on a project that had worked for days also returned 403 (list and read/write are different permissions). An unlisted game "dropped in search" because unlisted games don't show up in search. An oEmbed check returned 400 for public videos because the URL lacked `www`. Each time we were measuring our own call.

> **CLAUDE.md:** Before reporting an error code or "not found" as a finding, make the same call on a target known to work. If the control fails too, log it as a measurement problem and change nothing.

<sub>record #0762 · #0770 · #0605 · 2026-09</sub>

### 19. A "count" field filled by the model is not a count
We had a model extract quotes from reviews as `{quote, source, count}`. Of 307 quotes, about 300 appeared exactly once in the source, yet one quote seen once carried `count=60`, and the validation doc printed it as fact. The format was valid, so it passed. It was caught in review just before the next stage.

> **CLAUDE.md:** Never let the model fill countable values (counts, totals). Count them in code from the source, and show the model's number next to the computed one.

<sub>record #1201 · 2026-10</sub>

---

## 4. One keystroke from irreversible

### 20. Moved one config file; the backups had been dead for months
Cleaning a server home directory, the agent moved old-looking files to an archive folder after checking only the process manager and crontab. One was the config of a systemd-run DB backup tool. It restarted every 5 seconds, over 500,000 times. The backup chain had actually already been dead since an earlier path move, more than three months in total. To whoever reads that path, moving a file is the same as deleting it.

> **CLAUDE.md:** Before moving or deleting a file, grep its path across crontab, systemd units, container configs and all scripts.

<sub>record #0106 · 2026-07</sub>

### 21. An approved delete, and the target changed in between
We proposed deleting some untracked copy files and got approval. Meanwhile a parallel session committed and pushed exactly those files. They were now tracked originals. The agent deleted them on the old approval; `git restore` brought all five back. Approval covers the state at the time of the proposal.

> **CLAUDE.md:** Even for an approved delete, re-check the target's state (`git ls-files` / `git status`) right before running it. If the reason no longer holds, stop and ask again.

<sub>record #0270 · 2026-08</sub>

### 22. Running `--help` overwrote the status doc
A generator script for our status doc was run on a machine without its input data. It didn't crash; it overwrote the doc with "failure banner + previous snapshot". The same month, someone called it with `--help` to see usage. It had no argument parsing, so `--help` simply ran it: an empty glob, no error, a "0 items" doc over the original.

> **CLAUDE.md:** A script that overwrites an output must stop with failure before writing when its input is empty. Before passing `--help` to an unfamiliar script, read the source for argument handling.

<sub>record #0193 · #0252 · 2026-08</sub>

### 23. Imported a script for one function, and it ran again
To reuse one `call()` function, the agent imported yesterday's one-off script. Its work loop sat at module top level, so importing ran it: new playlists on two public video channels, a channel section added, description links changed again. Reverted within two minutes.

> **CLAUDE.md:** Never import a one-off script that writes to the outside world; copy the function instead. Put the body of every new script under `if __name__ == "__main__":`.

<sub>record #1308 · 2026-10</sub>

### 24. Re-ran an upload to see the error; the video went up twice
To look at an upload error, the agent ran the same command again. The second run uploaded, and the channel had the same video twice. Publish commands are not idempotent: "run it again to see" creates a real object in the world.

> **CLAUDE.md:** Never re-run an upload or publish command to inspect an error. Read the first run's output, and before any retry check whether the item is already live.

<sub>record #0821 · 2026-09</sub>

---

## 5. One repo, many hands: parallel sessions and git

### 25. A wrap-up commit swept up another session's work in progress
Two sessions worked in the same repo. One session's wrap-up script ran `git add -A`, so eleven of the other session's in-progress files landed in a commit titled after the first session's task. Nothing was lost, but history now lies about who did what.

> **CLAUDE.md:** With parallel sessions, commit only the paths of this task. Never `git add -A`.

<sub>record #0363 · 2026-09</sub>

### 26. The scope was empty, so it fell back to "everything"
Our wrap-up script took a path scope. One day the scope was `temp/` only, which `.gitignore` excludes entirely. With an empty scope the script quietly fell back to `add -A`, and hundreds of a parallel session's files were pushed in our commit. Adding them to `.gitignore` later didn't untrack them either.

> **CLAUDE.md:** If the commit scope is empty, fail; never fall back to everything. To untrack files already committed, add them to `.gitignore` and run `git rm --cached`.

<sub>record #0313 · 2026-08</sub>

### 27. "Out-of-scope files not added", yet the index went in
Files had been staged with `git add -A` before the scoped wrap-up script ran. The script said it hadn't added out-of-scope changes, and the agent reported those files excluded. They were in HEAD: `git commit` without paths commits the whole index. Sessions sharing a working tree share an index.

> **CLAUDE.md:** With parallel sessions, don't pre-stage. After committing, check `git show --stat HEAD` before reporting what went in.

<sub>record #0581 · #0296 · 2026-09</sub>

### 28. My edits vanished. They were hidden, not deleted.
Source edits disappeared several times while two sessions shared a repo. They were in a stash left by another session's interrupted `pull --rebase --autostash`, and once in an unreachable "autostash" commit that only `git fsck` could find. From the working tree it looks like loss, so you rewrite.

> **CLAUDE.md:** If edits vanish, before rewriting anything check `git stash list`, then `git reflog`, then `git fsck --unreachable`, in that order.

<sub>record #0429 · #0711 · #0943 · 2026-10</sub>

### 29. A timeout killed the rebase, and it still printed success
A `pull --rebase` was killed mid-pick by a command time limit. `rebase --continue` printed `Successfully rebased`, but our commit was in neither master nor the working tree, and a game build made from it was already public. Another day, `timeout 280 bash wrapup.sh | tail -3` died right after the autostash; push never ran, and exit was 0 because of `| tail`.

> **CLAUDE.md:** Never wrap a script that runs git rebase or pull in `timeout` or `| tail`. After an interruption, look at `git stash list` and reflog first.

<sub>record #0751 · #1037 · #1042 · 2026-10</sub>

### 30. The last save silently wins
Two sessions saved to the same memory key. One rewrote the summary; minutes later the other's save erased it. Next month, a session held a copy for 30+ minutes and saved it back over another session's newly recorded approval. No lock, no conflict error. A hook quoting the old text was the only reason anyone noticed.

> **CLAUDE.md:** Never save from a copy you've held a long time. Re-read right before saving and merge only your change into the fresh body.

<sub>record #0767 · #1013 · 2026-10</sub>

### 31. Saved a placeholder to learn the version value, twice in one day 🛡
After the memory store got optimistic locking, the agent sent a placeholder body to the *save* tool just to learn the version value from the rejection. Twice in one day, the second time after the lesson was already recorded. Both were rejected only because the guessed version lacked microseconds. A correct guess would have replaced the whole note with one line. Now `hooks/guard_short_save.py` denies saves under 300 characters.

> **CLAUDE.md:** Never use a save command to look up a value. Get version values with a read command, and send the full merged body when saving.

<sub>record #1088 · 2026-10 · 🛡 now blocked by a guard</sub>

---

## 6. Works on my machine

### 32. There was no `node` inside cron
An approved scheduled post ran as a one-shot cron job. The log showed a snapshot success and "done". No upload happened: the script called bare `node`, which lived under `~/.nvm`, which cron's PATH doesn't include. Cron doesn't read your login shell's setup.

> **CLAUDE.md:** Scripts run from cron must call node / python by absolute path or set PATH inside the script.

<sub>record #1182 · 2026-10</sub>

### 33. A leftover environment variable beat the config
Cloud login succeeded and the credential file existed, but every tool failed with `service-account.json was not found`: an old `GOOGLE_APPLICATION_CREDENTIALS` in `.bashrc` pointed at a deleted file, and it takes precedence. Another time an app got "high demand" / quota errors: the shell exported a free-tier API key, and the app's `.env` loader doesn't override existing variables. Both error messages pointed elsewhere.

> **CLAUDE.md:** For auth or API-key errors, check `env | grep` for leftover variables before re-logging in or retrying.

<sub>record #0065 · #1121 · 2026-10</sub>

### 34. The deploy succeeded, and the code was in no git anywhere
`gcloud run deploy` uploads the working tree; no commit needed. Over five sessions of deploys, the live code piled up uncommitted. Lose that machine, and production can't be reproduced or rolled back. Found by comparing git log with deployed revisions.

> **CLAUDE.md:** A successful deploy is not version control. Before ending a deploy session, check `git status` and commit what you deployed.

<sub>record #0062 · 2026-07</sub>

---

## 7. What someone else's API told us

### 35. Read page one of a list as the whole list
A product-list API returns 10 items per page. A creation script judged "does this exist?" from page one and created a real duplicate draft. A month later, one call to the same API showed 10 of 17 products; a sales monitor built on that call would never have seen the other 7. Pagination raises no error. It just adds a next-page key.

> **CLAUDE.md:** To judge existence or totals from a list API, follow the next-page key until it's gone, and print the count received.

<sub>record #0491 · #1079 · 2026-10</sub>

### 36. Reasoning tokens ate the output budget: cut, empty, and billed
A thinking model called with an old non-thinking output budget: answers truncated, a day's quota burned. A reasoning model called with `max_tokens` 1200: all 10 responses had an empty body, and output was billed to the limit. Another model at 6000 tokens cut off mid-sentence with no error; at 24000 it finished. A truncated answer looks like a short answer.

> **CLAUDE.md:** Give reasoning models a generous output limit and print `finish_reason` and usage every time; treat `length` as failure. Check the output format with one call before a batch.

<sub>record #0326 · #0355 · #0863 · 2026-09</sub>

### 37. The fix script failed, and the paid submission ran anyway
A prompt-fixing script and a paid generation call were chained with `;`. The fix hit an assert and exited non-zero; `;` runs the next command regardless. The exact old prompt we were fixing was submitted: four paid generations wasted.

> **CLAUDE.md:** Never chain a billed command with `;`. Use `set -e` or `&&`.

<sub>record #0810 · 2026-09</sub>

### 38. One headless look at our shop, and the seller IP got bot-flagged 🛡
To check our own shop page on a handmade marketplace, the agent took one headless screenshot from the PC. Response: `Access is temporarily restricted … automated activity on your network`, on the same IP as the seller account. The block is per network, not per account. Now `hooks/guard_bash.py` denies headless or curl access to that site's web pages; the official API host stays allowed.

> **CLAUDE.md:** Never open a marketplace's web pages headlessly or with curl from the same network as your seller account. Use the official API or a human's screenshot.

<sub>record #1155 · 2026-10 · 🛡 now blocked by a guard</sub>

---

## 8. Who ends up reading it

### 39. `.gitignore` said `venv/`; the folder was `.venv`
`git add -A` staged the entire virtual environment, about 1,600 files, because `venv/` doesn't match `.venv/`. A pre-commit size check caught it. (Python 3.13+ `venv` now writes its own `.gitignore`, so new environments are safe; older ones aren't.)

> **CLAUDE.md:** Match `.gitignore` patterns against the real folder names. After `git add -A`, check for staged files over 1 MB before committing.

<sub>record #0098 · 2026-07</sub>

### 40. The banned-word list lived in the old generator 🛡
A new product generator put a famous TV game show's segment name into a page, a PDF and three images. That name was already on a banned list, inside a *neighbouring* generator's validator. The new one never passed through it. It was caught on a second legal pass before upload. Now the trademark check sits at the shared pre-upload step (`tools/ship_check.py`), which every product passes regardless of generator.

> **CLAUDE.md:** Put trademark and banned-word checks at the common pre-upload step, not inside one generator. When you add a generator, confirm the existing list applies to its output.

<sub>record #1180 · 2026-10 · 🛡 now blocked by a guard</sub>

---

## 9. The harness and the shell

### 41. The hook couldn't find its script, so every Bash call was blocked
A PreToolUse hook located its checker via `$CLAUDE_PROJECT_DIR`. Testing showed that if that variable was empty, every Bash call in the session was blocked. The checker hadn't judged anything: the interpreter couldn't find the file and exited with 2, the same code as "block". A safety net that fails closed on its own bugs gets removed, and then there's no net.

> **CLAUDE.md:** Hooks must warn and pass on their own failures (missing script or variable). Exit code 2 (block) only when the check actually found a danger.

<sub>record #0345 · 2026-09</sub>

### 42. A block-once hook blocked forever: the key changed every call
A hook was meant to block the first Read once (with a tip), then let retries through via a marker file named with `$PPID`. Reads kept getting blocked, and marker files piled up. Each hook call runs in a fresh shell with a new parent PID. Read and Edit were both stuck.

> **CLAUDE.md:** If a hook must remember state between calls, key it on `session_id` from the hook's input JSON, not `$PPID`.

<sub>record #0052 · 2026-07</sub>

### 43. The dangerous-command hook blocked the README that described the command
Right after adding dangerous-command patterns to a PreToolUse hook, writing a README that *mentioned* those commands was blocked: the text was inside a heredoc, and the hook scanned the whole command string. Frequent false positives get guards switched off, and then the original accident comes back.

> **CLAUDE.md:** Command-checking hooks should treat heredoc bodies as data (but keep checking if ssh / scp / rsync appear outside the heredoc). Test new guards against doc-writing commands too.

<sub>record #0339 · 2026-09</sub>

### 44. `pkill -f` killed its own shell; `pgrep -f` waits never ended 🛡
`pkill -f 'server.js'` killed Claude's Bash tool shell (exit 144) instead of the server. `while pgrep -f "<script>"` loops never ended, and the agent reported finished batches as running. Claude Code runs your command as `bash -c '<whole command>'`, so the pattern is in that shell's own command line too. After it was written down as a rule, it still repeated several more times in two days. Now `hooks/guard_bash.py` blocks it.

> **CLAUDE.md:** With `pkill -f` / `pgrep -f`, use a bracket pattern (`[s]erver.js`) or a PID file. Never put a bare `pgrep -f` pattern in a wait-loop condition.

<sub>record #0420 · #0815 · #0518 · #0816 · #0977 · #1060 · 2026-10 · 🛡 now blocked by a guard</sub>

### 45. Research agents spawned research agents, then all died together
Several coordinator agents were launched for deep research with no ban on the Agent tool. Each split its batch into more sub-researchers. They shared one session's usage limit and web-search limit; when it ran out, all of them died at once, with no intermediate results saved.

> **CLAUDE.md:** In every subagent prompt, forbid spawning subagents, cap web calls per agent, and require partial results to be written to a file as they go.

<sub>record #1077 · 2026-10</sub>

### 46. A rule for every task, written in a section with an expiry date
A rule meant for all work was placed inside a dated, temporary section and in a doc opened only on demand. It would have vanished when the section expired, and sessions on another device never saw it at all. Claude Code's auto-memory has the same limit: it stays on one machine. Where a rule applies is decided by when and where the file is read.

> **CLAUDE.md:** Rules for all work go in the undated, permanent part of the `CLAUDE.md` that every session loads and git shares. Not only in dated sections, on-demand docs or auto-memory.

<sub>record #0704 · 2026-09</sub>

### 47. Pipe plus heredoc: Python read empty input instead of the data
`cmd | python3 - <<EOF` was meant to let the script `json.load(sys.stdin)` the command's output. Python got empty input and died with `JSONDecodeError`. There is one stdin: the heredoc replaced the pipe, and `python3 -` reads the script itself from stdin.

> **CLAUDE.md:** Never combine a pipe and a heredoc like `cmd | python3 - <<EOF`. Pass the script by heredoc and the data by environment variable or temp file.

<sub>record #0009 · 2026-06</sub>

---

## 10. Notes that drift

### 48. Promises without an owner: 48 hours, nobody started
The agent wrote four next steps; three were its own (a measurement, a freeze, an upload). For 48 hours nobody started them. Written in a "reporting to the human" voice, they read as the human's tasks, and the agent waited for approval.

> **CLAUDE.md:** Give every next step and promise an owner (AI / user). Items the AI owns are the first work of the next session.

<sub>record #0354 · 2026-09</sub>

### 49. A plan written in the present tense
A runbook described a script that didn't exist yet. A shared engine's README said seven games had migrated; measured: zero. A strategy doc called one channel "the derivative channel"; it had one video, while finished episodes piled up unposted for ten days. Sentences have no tense marker for "planned". The next session builds on them as fact.

> **CLAUDE.md:** Never describe files, features or channels that don't exist yet in the present tense. Mark plans as plans, and write counts from grep, with the command.

<sub>record #0135 · #0473 · #0623 · 2026-09</sub>

### 50. Three docs said 10 chapters; the source had 15
A handoff doc, a plan doc and the work notes all said a learning app had 10 chapters. The source file defining them had 15. That number decided what to ship first. Three documents copying each other is one piece of evidence, not three.

> **CLAUDE.md:** Count quantities (counts, versions) from the source, not from docs. Docs agreeing with each other is not verification.

<sub>record #0362 · 2026-09</sub>

---

*Want the other 250+ in English? Star [the repo](https://github.com/hadiux0295/claude-code-mistake-guards), and use Watch → Releases to get a note when the translation ships. That's how we decide whether to translate the full log.*
