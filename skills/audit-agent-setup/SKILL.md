---
name: audit-agent-setup
description: Runs the Left the Chat static audit on a directory of SKILL.md, AGENTS.md, or CLAUDE.md files and prints findings. Use for local agent-setup review. Not for runtime telemetry comparison (use the page) or unrelated code review.
allowed-tools: Read, Glob, Grep, Bash
---

# Audit agent setup

Run the same static checks the Left the Chat page and its pre-commit hook use, at
full local depth, against a directory the user names.

## Steps

1. Ask which directory to audit if not given. Default to the current directory.
2. Run: `node scripts/audit.mjs <directory>`
3. Print the output as-is: findings grouped critical, then major, then minor.
4. If this is the first time this skill has run in this repo, offer to enable the
   pre-commit hook (`tools/audit-staged.mjs`) per plan decision D-24. The hook ships
   disabled by default and only fires when a PR is open. Ask before enabling it;
   never enable it unasked.

## Notes

- This is the static half only. Declared-versus-actual findings (a tool granted but
  never called, a skill that never fires) need runtime telemetry, which this CLI
  does not have. For that comparison, use the Left the Chat page and paste in a
  session log.
- Read-only. This skill never edits, moves, or deletes a file.
