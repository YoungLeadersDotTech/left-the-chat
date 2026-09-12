# Left the Chat — AI Studio

```bash
npm install
npm run dev
```

A privacy-first, deterministic audit loop for agent setup files and runtime telemetry.
Everything runs in the browser: no backend, API key, upload, or network call is required.

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

## Hackathon context

Team **Left the Chat** - AI Tinkerers Dublin hackathon, "Agents, Everywhere", 12 September 2026.

## Status

Nothing here is the submission yet. The project and its core functionality are to be built
during the hackathon period on 12 September 2026, per the event's eligibility rule. This repo
exists ahead of the day so there is somewhere to push to, and so the history honestly shows
what was scaffolding and what was built on the day.

## Build day

- Build window: 10:00 to 17:00 local, 12 September 2026
- Submission deadline: 17:00 IST, 12 September 2026
