---
name: eval-scout
description: "Scan skill files across plugins and global skills to identify candidates for promotion to eval alumni. Scores each against 4 criteria (domain depth, evaluation perspective, testable output, cross-domain reach) and outputs a ranked candidate report."
user-invocable: true
disable-model-invocation: false
allowed-tools:
  - Read
  - Glob
  - Grep
  - AskUserQuestion
  - TaskCreate
  - TaskUpdate
  - TaskGet
  - TaskList
version: 1.0.0
category: Workflow
tags:
  - evaluation
  - eval-alumni
  - skill-discovery
  - scouting
last-updated: 2026-03-21
---

# Eval Scout - Find Evaluator Candidates Among Skills

Scans skill files to identify which ones have enough domain depth to become contracted eval alumni members.

Auto-invoke when the user says "scout for evaluators", "find eval candidates", "which skills could be evaluators", "eval scout", or runs `/aios-eval:eval-scout`.

Skip for: running evaluations (use the eval skill), adding a known member (use add-eval-member), or validating existing eval agents (use agent-validate).

## When to Run

- After a batch of new skills are created (e.g., post-migration)
- Periodically to check if accumulated knowledge warrants new evaluators
- When a new domain area gets significant skill coverage

## Workflow

### Step 1: Classify scan scope (triage before the glob loop runs)

Before scanning anything, classify which corpus to scan - this determines which glob
patterns run in Step 2:

```
AskUserQuestion: "Which skills should eval-scout scan?"
  A) Everything - both repos plus global skills (default, matches all 3 patterns below)
  B) Personal repo only (ai-os-personal)
  C) Toast repo only (ai-os-jc-toast)
  D) Global skills only (~/.claude/skills)
```

### Step 2: Discover skills to scan

TaskCreate one task for the scan-and-score pass before running the globs below.
TaskUpdate to in_progress when scanning starts, TaskGet to check status if resuming a
partial scan, and TaskUpdate to completed once Step 3 (scoring) finishes.

```
Glob patterns (scan in order, filtered to the scope chosen in Step 1):
  1. ~/Projects/ai-os-jc-toast/plugins/*/skills/*/SKILL.md
  2. ~/.claude/skills/*/SKILL.md
  3. ~/Projects/ai-os-personal/plugins/*/skills/*/SKILL.md

Exclude (already eval-related):
  - plugins/aios-eval/skills/*
  - Any skill with tag "eval-contractor" or "evaluation"
```

### Step 3: Score each skill against 4 criteria

For each SKILL.md, read the description and body, then score:

| Criterion | Weight | What to assess | Score 0-25 |
|-----------|--------|----------------|------------|
| **Domain depth** | 25 | Does the skill contain deep, specific domain knowledge (business rules, gotchas, field mappings)? Not just tool syntax but understanding of WHY. | 0 = generic tool wrapper, 25 = deep domain with edge cases |
| **Evaluation perspective** | 25 | Could this skill's knowledge be used to EVALUATE other work? Can it spot mistakes, missing considerations, or incorrect assumptions in its domain? | 0 = pure execution, 25 = clear right/wrong criteria |
| **Testable output** | 25 | Can evaluations from this domain produce concrete, actionable findings? Not vague "consider X" but specific "this field should be Y because Z". | 0 = subjective only, 25 = verifiable claims |
| **Cross-domain reach** | 25 | Does this domain touch other domains in ways that generalists would miss? Would having this evaluator catch blast radius? | 0 = isolated, 25 = high cross-team impact |

**Total**: 0-100. Threshold for candidacy: **60+**

### Step 4: Filter and rank

```
candidates = [s for s in scored_skills if s.score >= 60]
candidates.sort(by=score, descending)
```

### Step 5: Present results

```
AskUserQuestion: "Eval scout found {N} candidates. Review?"
  A) Show full report (all candidates with scores + reasoning)
  B) Show top 3 only
  C) Save report and exit
```

**Report format**:
```markdown
## Eval Scout Report - {date}

### Candidates (score >= 60)

| Rank | Skill | Plugin | Score | Domain depth | Eval perspective | Testable | Cross-domain |
|------|-------|--------|-------|-------------|-----------------|----------|--------------|
| 1 | salesforce-knowledge | toast-bsa | 85 | 23 | 22 | 20 | 20 |
| 2 | btt-domain-knowledge | toast-bsa | 78 | 25 | 18 | 15 | 20 |
| ... | | | | | | | |

### Detailed Assessment: {top candidate}

**Why this skill could be an evaluator**:
- {specific domain knowledge that enables evaluation}
- {types of mistakes it could catch}
- {cross-domain impacts it would flag}

**Suggested contracted member name**: eval-{domain}-contractor
**Prerequisite**: Stakeholder persona exists? {yes/no}

### Not Ready Yet

| Skill | Score | Gap | What's missing |
|-------|-------|-----|----------------|
| tool-patterns | 42 | 18 | Tool syntax without domain judgement |
| ... | | | |
```

### Step 6: Offer next action

```
AskUserQuestion: "What next?"
  A) Create a contracted member from top candidate (runs add-eval-member)
  B) Save report to memory and exit
  C) Re-scan with different threshold
```

**Report save location**: `~/work-registry/memory/domain/eval-alumni-candidates.md`

## Scoring Examples

**High score (85+)**: `salesforce-knowledge` - deep SF architecture, knows trigger framework gotchas, can spot incorrect DAL patterns, touches billing/NetSuite/eComm.

**Medium score (60-75)**: `btt-domain-knowledge` - good business rules but evaluation perspective is more "is this the right product decision" than "is this technically correct."

**Low score (<60)**: `tool-patterns` - knows Jira CLI syntax but can't evaluate whether a Jira ticket's content is correct. Pure execution knowledge.

## Integration

- **Feeds into**: `add-eval-member` skill (H1 design doc)
- **References**: H1 design doc at `~/Projects/johns-publisher/brainstorming-sessions/2026-03-21-eval-alumni-design/`
- **Output consumed by**: coordinator agent (discovers new contractors by `eval-contractor` tag)
