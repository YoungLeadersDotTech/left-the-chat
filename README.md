# Left the Chat AI Studio

```bash
npm install
npm run dev
```

A privacy-first, deterministic audit loop for agent setup files and runtime telemetry.
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

## Claude Code evaluation plugin

This repository bundles `aios-eval` version 2.5.0 in
`.claude/skills/aios-eval`. Collaborators do not need access to the original
private marketplace. Commit and share this directory with the repository.

Start a current version of Claude Code from the repository root and accept its
workspace trust prompt. Claude discovers the bundled plugin as
`aios-eval@skills-dir`. Start a new session if you added the files while Claude
was already running.

Run `/aios-eval:eval` to evaluate code, documents, skills, or agents. The bundle
contains three skills and eleven agent definitions.

If your Claude Code version does not discover skills-directory plugins, launch
from the repository root with:

```sh
claude --plugin-dir ./.claude/skills/aios-eval
```

Validate the bundle with:

```sh
claude plugin validate .claude/skills/aios-eval
```

### Scope and limitations

The evaluation components are bundled locally. The additional `eval-scout` and
`eval-scout-generate` workflows contain upstream assumptions about personal
directories, work-registry output, private repositories, and related authoring
tools. Those workflows need adaptation before collaborators use them to discover
or publish new evaluators. Bundling this plugin does not provide those external
tools or repository permissions.

Python 3.10 or later is required only for the included Python validators.
Running their tests also requires pytest.

This is a vendored snapshot from the supplied `aios-eval.zip`, not a subscription
to marketplace updates. Archive metadata, Python caches, pytest caches, and an
old README backup were excluded. The plugin's manifest and version are retained
from the supplied release.

See [the bundled plugin README](.claude/skills/aios-eval/README.md) for component
details, and [Claude Code's skills-directory plugin documentation](https://code.claude.com/docs/en/plugins-reference#skills-directory-plugins)
for discovery and trust behavior.

## Hackathon context

Team **Left the Chat**, AI Tinkerers Dublin hackathon, "Agents, Everywhere", 12 September 2026.
