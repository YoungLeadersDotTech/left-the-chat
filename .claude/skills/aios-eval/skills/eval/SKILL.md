---
name: eval
description: "Run an evaluation committee review - invoke all 7 expert alumni [AI] for comprehensive assessment of skills, agents, docs, or code, or target specific experts by domain. Produces per-expert scores, synthesis, and recommendations."
user-invocable: true
disable-model-invocation: false
allowed-tools:
  - AskUserQuestion
  - Read
  - TaskCreate
  - TaskUpdate
  - TaskGet
  - TaskList
version: 1.0.0
category: Workflow
tags:
  - evaluation
  - committee
  - review
  - quality
  - eval-alumni
last-updated: 2026-03-21
---

# Eval Alumni Committee

Run a structured evaluation using the 7-expert committee or a targeted subset.

## When to use

Auto-invoke when the user says "evaluate this", "run eval", "committee review", "get expert feedback", "check this against the committee", "score this", "eval alumni review", or runs `/aios-eval:eval`.

Skip for: validating skills (use skill-validation-workflow), validating agents (use `agent-development-toolkit-toast:agent-validate`), general code review not using the eval alumni committee.

## Expert Roster

| Expert | Alias | Domain |
|--------|-------|--------|
| Dr. Ava Nakamura [AI] | `eval-alumni-dr-nakamura` | AI systems, Claude best practices, token efficiency |
| Prof. "Doc" Hartwell [AI] | `eval-alumni-doc-hartwell` | Technical correctness, algorithms, design patterns |
| Sam "AccessFirst" Rodriguez [AI] | `eval-alumni-sam-rodriguez` | Cognitive accessibility, directory structure, naming |
| Riley "Chaos Navigator" Chen [AI] | `eval-alumni-riley-chen` | Product/UX, workflow, rapid prototyping |
| "Practical Jack" Morrison [AI] | `eval-alumni-jack-morrison` | Real-world feasibility, maintenance, pragmatic trade-offs |
| Capt. Sarah "SecOps" Winters [AI] | `eval-alumni-sarah-winters` | Security, PII, auth patterns, deployment |
| Zara "DevRel" Okafor [AI] | `eval-alumni-zara-okafor` | Documentation quality, DX, contribution workflows |

## Workflow

### Step 1 - Classify mode (triage before any tool loop runs)

Before invoking any expert, classify the request into one of three modes - this
determines which experts run and in what order, so it must happen first:

```
AskUserQuestion: "Which evaluation mode?"
  A) Full committee - all 7 experts (comprehensive, ~7 sequential runs)
  B) Targeted - select specific expert(s) by domain
  C) Coordinator only - orchestrate and synthesise results already at hand
```

### Step 2 - Choose target (if targeted mode)

```
AskUserQuestion: "Which expert(s)?" [multiSelect: true]
  - AI/Claude systems → Dr. Nakamura [AI]
  - Technical correctness → Doc Hartwell [AI]
  - Accessibility/UX → Sam Rodriguez [AI]
  - Product/UX → Riley Chen [AI]
  - Practical feasibility → Jack Morrison [AI]
  - Security → Sarah Winters [AI]
  - Documentation/DX → Zara Okafor [AI]
```

### Step 3 - What to evaluate

```
AskUserQuestion: "What are we evaluating?"
  - Paste content or description
  - Or provide file path (will be Read)
```

### Step 4 - Run evaluation(s)

Use TaskCreate to add one task per expert before invoking any of them, so progress is
tracked as each committee member reports back. For each expert:
1. TaskCreate: "{expert} review of {target}"
2. TaskUpdate: mark in_progress, then invoke the agent via `subagent_type: "aios-eval:{agent-name}"`
3. Pass evaluation target + scoring instructions
4. Collect: score (0-100), findings, recommendations
5. TaskUpdate: mark completed once that expert's result is collected
6. TaskGet / TaskList: check status across experts if resuming a partial run

For **full committee**: run in sequence, each expert evaluates independently.
For **targeted**: run only selected expert(s).

### Step 5 - Synthesise (full committee or multi-expert)

Invoke `eval-alumni-coordinator` to:
- Weight scores by domain relevance (weights are deterministic, not model-improvised -
  see the fixed per-domain weighting table in `agents/eval-alumni-coordinator.md`)
- Identify consensus findings
- Surface conflicting assessments
- Generate executive summary with overall score

### Step 6 - Present results

```
## Evaluation Results

Overall Score: {weighted average}/100
Experts: {list}

### Per-Expert Scores
| Expert | Score | Top Finding |
|--------|-------|-------------|

### Key Recommendations (Must Fix)
...

### Should Fix
...

### Production Readiness
{READY / READY WITH WARNINGS / NOT READY}
```
