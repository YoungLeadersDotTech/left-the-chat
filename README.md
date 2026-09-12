# Left the Chat — AI Studio

```bash
npm install
npm run dev
```

A composable React workspace for prototyping AI conversations, streaming responses,
and live model controls. It starts without environment variables and uses a clearly
labelled mock model until a server-side API key is provided.

## Configuration

Copy `.env.example` to `.env` only when you want to connect a model. Never prefix
the API key with `VITE_`; the development proxy reads `OPENAI_API_KEY` server-side,
and all client model traffic passes through `src/lib/ai.js`.

## Scripts

- `npm run dev` starts the app at `http://localhost:5173`.
- `npm run build` creates a production build in `dist/`.
- `npm run preview` serves the production build locally.

## Project shape

- `src/components/` contains reusable UI primitives and panels.
- `src/pages/` composes product surfaces from those primitives.
- `src/state/` owns shared React context and hooks.
- `src/lib/ai.js` is the single client adapter for model calls.
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
