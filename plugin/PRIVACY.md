# Privacy — Mistake Guards plugin

Applies to the Claude Code plugin in `plugin/` (synura-mistake-guards).

- **What it reads:** only the Bash tool call Claude Code passes to the hook on stdin (the command text, and the transcript path, used to name the user's `~/.claude` folder inside an in-memory string). It opens no other file and reads no environment variable.
- **What it stores:** nothing. It writes no files and keeps no state between calls.
- **What it sends:** nothing. It makes no network connections. Its only output is a deny message to Claude Code on stdout, or an error line on stderr.
- **Personal data:** none collected, stored or shared. No analytics, no telemetry.
- **Retention:** not applicable; nothing is retained.

The copy-install templates elsewhere in this repository are not part of the plugin; read their own files before using them.

Contact: hello@synuracore.com · Publisher: SynuraCore (https://synuracore.com)
