---
name: eval-scout-generate
description: Extension to eval-scout. When a committee run needs a specialist evaluator that does not exist, generate one under a fixed template, or extend the closest library evaluator if the gap is small. New evaluators upstream as GitHub PRs.
version: 1.1.0
upstream-source: https://github.com/YoungLeadersDotTech/ai-os-personal
last-updated: 2026-07-29
---

# Eval Scout - Generate / Extend Evaluators On Demand

The original eval-scout *discovers* which existing skills could become evaluators.
This extension handles the other direction: a committee run needs an expert lens the
roster does not have, so the scout either extends the closest existing evaluator or
generates a new one - always under tight constraints so generated evaluators stay
consistent and never drift into bespoke one-offs.

## Trigger

During a committee evaluation (eval or eval-competition), the artifact type calls
for a specialist the roster lacks. Examples grounded in real gaps:
- A **comic** format needs a comic-craft critic (panel composition, visual character,
  whether it reads as a comic or as boxes).
- A **teaching/enablement** artifact needs a learning-design critic (does it actually
  teach, or just present).
- A **visual/diagram** format needs a UX-visual critic beyond generic accessibility.

## The library-gap protocol (check before generating)

Generating a brand-new evaluator is the last resort, not the first move. In order:

1. **Scan the evaluator library** (the eval-alumni roster plus any previously
   generated evaluators saved to the library) for the closest lens.
2. **Assess the gap, do not just ask.** Judge how far the closest evaluator is from
   what is needed:
   - *Small gap* (the evaluator covers the domain but lacks one criterion, e.g. the
     UX critic has no panel-composition criterion): the gap is in that library
     evaluator. The right move is to **update the library evaluator**, because the
     gap will recur for everyone. Propose the specific added criterion.
   - *Large gap* (no evaluator is in the right domain at all): generate a **new**
     evaluator.
   - *Genuinely ambiguous* (could be either, or the domain is unfamiliar): this is
     the only case where you **ask the user** - update existing or create new - and
     you ask with a concrete recommendation, not an open shrug.
3. Never silently invent a new evaluator when an existing one is one criterion short.
   That is how a library rots into duplicates.

## The fixed generation template (consistency guard)

Every generated or extended evaluator MUST follow this exact shape - nothing more,
nothing less. This is what keeps generated evaluators consistent enough to score the
same artifact the same way twice. The scout fills only the bracketed parts.

Per the `eval-committee-deterministic-validators` retrofit (`ai-os-jc-toast` builder-plans
folder), the committee-wide model is **deterministic-first, not scoring-first**: a criterion is
only ever asked of an LLM to eyeball when no objective test exists for it. Generated evaluators
follow the same rule as the 7 standing alumni - each of the five criteria is checked against the
deterministic bar below BEFORE it is written down as a bare 0-100 line. Most generated criteria
will still land subjective (a brand-new domain's craft/voice judgment calls rarely have an
objective test), and that is the expected, correct outcome, not a shortfall.

```markdown
---
name: eval-alumni-[domain-slug]
description: [One line: the lens this evaluator brings and what it can catch.]
tools: [Read, Grep, Glob, TaskCreate, TaskUpdate, TaskGet, TaskList]
version: 1.0.0
persona: [domain-slug]
expertise: [domain]
evaluation_focus: [3 focus phrases]
rule_prefix: [3-4 uppercase letters, unique]
generated_by: eval-scout-generate
generated_on: [date]
effort: xhigh
---

# [Evaluator name] - [one-line role]

## When invoked
[The artifact types and committee situations that call for this lens.]

## Evaluation Criteria

**Rubric mode annotation**: criteria carrying an inline `[MODE: deterministic | ...]` or
`[MODE: deterministic-pending | ...]` tag are backed by a real (or planned) deterministic check -
see `phase2-rubric-annotation-convention.md` (`ai-os-jc-toast` builder-plans folder) for the tag
grammar and `validators/deterministic_verdict.py` (this plugin) for how Step 4.0 of the `eval`
skill consumes it. Criteria with no tag are genuinely-subjective and are scored by persona
judgment exactly as before. This legend line is added once per generated evaluator, regardless of
whether any row below ends up tagged.

### The five criteria (fixed count - exactly five, each scored 0-100 to the quality bar unless deterministic)
<!-- Row shape depends on the mode classified below - three examples, pick the one that applies
     to each criterion (do not literally include this comment or the alternative rows in the
     generated file - one row per criterion, in the form its classification calls for):
     - reused check:      1. **Security** [MODE: deterministic | criterion_id=C-W1 | check_ids=SEC-001,SEC-003 | source=live-artifact-scan] - [description]
     - new but buildable:  1. **[Criterion]** [MODE: deterministic-pending | criterion_id=[rule_prefix]-1] - [description]
     - genuinely subjective (the default, no tag): -->
1. **[Criterion]** - [what excellent vs competent looks like in concrete terms]
2. **[Criterion]** - [...]
3. **[Criterion]** - [...]
4. **[Criterion]** - [...]
5. **[Criterion]** - [...]

## Scoring anchors (must reference the quality bar, not defect-absence)
- 90+: [domain-specific picture of crafted excellence, not merely correct]
- 70-79: [domain-specific picture of competent-but-bland]
- below 70: [a real fault in this domain]

## Output format
[A short, fixed output block: per-criterion score or deterministic verdict, worst fault,
highest-value fix.]
```

### Classifying each criterion's mode (deterministic-first, per the committee-wide retrofit)

For each of the five criteria, before writing it into the template apply the same rigor bar
`criteria-classification.md` (T-03) used across the whole committee: **"could I write a script
that proves this criterion true or false" is the bar, not "does this sound objective."** Then:

1. **Reuse, don't fork.** Check the criterion against the existing deterministic-check registry
   first - the routing table in `phase2-output-contract.md` and the real `C_*_CHECK_IDS`
   constants in `validators/deterministic_verdict.py` (`C_W1_CHECK_IDS`, `C_W2_CHECK_IDS`,
   `C_R5_CHECK_IDS`, `C_N4_CHECK_IDS`, `C_H1_CHECK_IDS`). If the generated criterion is
   substantively the same check as an already-classified one (e.g. a generated evaluator's own
   "Security" criterion duplicating C-W1's Security Vulnerabilities), tag it `deterministic` and
   reuse that criterion's real `criterion_id`/`check_ids`/`source` verbatim - never invent a
   parallel, redundant check for a domain the registry already covers.
2. **New but concretely buildable.** If the criterion is genuinely new to this generated
   evaluator AND a deterministic check is concretely describable (a script/grep/schema check that
   produces pass/fail, not a vague aspiration), tag it `deterministic-pending` with a fresh
   `criterion_id` of the form `[rule_prefix]-[n]` (e.g. `COMC-2`) - no `check_ids`/`source` yet,
   since nothing real exists to name. Record what the check would need to do as a one-line
   "Deterministic check needed" note in the Growth PR body (below) so a follow-up task can build
   it with a real TDD pair, mirroring T-08a/b's/T-12a/b's pattern for the standing criteria - the
   check itself is out of scope for generation.
3. **Genuinely subjective (the default).** No tag at all. This is the expected outcome for most
   criteria on a brand-new domain - craft, voice, "does it read as X" judgment calls almost never
   have an objective test. Do not force a tag just to make a generated evaluator look more
   rigorous than it is; that is the exact "sounds objective" anti-pattern the T-03 bar above
   exists to catch.

Hard rules the scout enforces on generation:
- Exactly five criteria. Not three, not eight - five keeps evaluators comparable.
- Scoring anchors must reference the quality bar (excellence = craft), never the old
  "no meaningful gaps" defect-absence language.
- A unique rule_prefix (check the roster for collisions).
- No persona theatrics beyond a one-line role - generated evaluators are lean and
  about the lens, not a character.
- Classify every criterion's mode per the section above before finalizing the rubric; tag
  `deterministic`/`deterministic-pending` rows per the T-07 convention, and always add the
  one-time `## Evaluation Criteria` legend line - even on evaluators where all five criteria end
  up subjective, so a reader never has to guess whether the absence of tags was a decision or an
  oversight.
- Never fabricate `check_ids` or a `source` value - both must trace to a real entry in
  `validators/deterministic_verdict.py`'s registry (reuse case) or be left blank under
  `deterministic-pending` (new-but-unbuilt case). A tag with invented check IDs is worse than no
  tag: it tells Step 4.0 to run a check that does not exist.

## Growth - upstream as a GitHub PR

A generated or updated evaluator is a contribution to the library, not a local
throwaway. When the user has a GitHub connection:

1. Save the evaluator to the local evaluator library first (so this run can use it).
2. Open a **pull request to the upstream source repo** named in the rubric's
   `upstream-source` field - for the skills-toolkit that is
   `YoungLeadersDotTech/ai-os-personal`; for the Toast variant it is the
   `ai-os-jc-toast` repo (where the persona libraries live). The PR adds the new
   evaluator file or the updated criterion, with a body explaining the gap it fills. If any
   criterion was tagged `deterministic-pending` (see the classification section above), the PR
   body includes its one-line "Deterministic check needed" note per criterion, so the follow-up
   check-building task has a concrete starting point instead of re-deriving the classification.
3. If there is no GitHub connection, save locally and tell the user the PR step was
   skipped, with the file path so they can upstream it manually.

The library is meant to grow the same way the persona libraries grow: each real gap,
once filled well, becomes permanent and shared rather than re-improvised next time.

## Effect on the ledger ratchet (a deliberate consequence)

The quality ledger ratchets - it rejects scores below the recorded best so quality
only climbs. When the *rubric itself* changes and gets harder, that assumption
inverts: an honest re-score under the new bar is correctly *lower*, and must be
recorded with `--allow-regress` and a `RUBRIC CHANGE` note in the findings, so the
drop is legible as a recalibration rather than a regression in the work.

Known limitation to fix in the ledger next: after a rubric change the ledger's
`next_target` still points at the old high-water mark. Until the ledger learns to
reset its baseline on a rubric-version bump, record the new rubric version in the
findings so a reader can see why the numbers moved. The drop is the bar telling the
truth; the room it reopens is the point.
