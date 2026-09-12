# Left the Chat AI Studio

```bash
npm install
npm run dev
```

A privacy-first, deterministic audit loop for prompt files and runtime telemetry.
Everything runs in the browser. No backend, API key, upload, or network call is required.

## Standalone build

Run `npm run build`, then copy `dist/index.html` anywhere. JavaScript and CSS are
inlined, so the file can be opened directly without a server.

## Scripts

- `npm run dev` starts the app at `http://localhost:5173`.
- `npm run build` creates a production build in `dist/`.
- `npm run preview` serves the production build locally.

## Project shape

- `src/components/` contains reusable UI primitives and panels.
- `src/lib/audit.js` contains deterministic setup checks and prompt generation.
- `src/lib/parsers.js` normalizes Claude Code, OpenCode, JSON, and JSONL telemetry.
- `src/lib/deterministic.js` provides stable serialization and SHA-256 hashing.
- `src/styles/` contains theme tokens and plain CSS.

Note: a vendored Claude Code evaluation plugin used during development was removed before publication because it is internal tooling.

## Plugin

The same static audit also ships as a Claude Code plugin, so it can run against real
files on disk instead of pasted text.

```
/plugin install prompt-auditor
```

This installs the `audit` skill (`skills/audit/SKILL.md`, invoked as
`/prompt-auditor:audit`),
which runs `scripts/audit.mjs` against a directory of `SKILL.md`, `AGENTS.md`,
`CLAUDE.md`, or `agents/*.md`/`skills/*.md` files and prints findings, grouped
critical then major then minor. It also offers to enable the pre-commit hook
(`tools/audit-staged.mjs`), disabled by default, on first run.

Verified with `claude plugin validate .` from the repo root.

## Hackathon context

Team **Left the Chat**, AI Tinkerers Dublin hackathon, "Agents, Everywhere", 12 September 2026.
