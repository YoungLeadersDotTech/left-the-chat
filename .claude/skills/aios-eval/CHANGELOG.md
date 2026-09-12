# Changelog - aios-eval

## 2.5.0 - 2026-09-11

### Added
- **`eval-alumni-codification-judge` [Eval Codify]** (T-14, ported from `ai-os-jc-toast`'s
  `toast-eval-committee`, `toast-eval-committee-consolidation` plan): evaluates whether
  prompt-only behavior should move into code, metadata, schemas, or helper tools. Registered in
  `plugin.json`'s `agents` array.
- **Codification Judge wired into the coordinator's scoring surfaces** (T-15): a
  "Codification Readiness: Codification Judge [AI] (50%), Dr. Nakamura [AI] (30%), Doc Hartwell
  [AI] (20%)" row added to Individual Expert Score Weighting, and a "Codification Readiness"
  entry added to the Priority Assessment Framework, mirroring the pattern already established for
  this persona in `toast-eval-committee`'s own Domain Weighting table.

### Known gap (out of scope for this release, noted for follow-up)
- The coordinator's "Committee Overview" roster narrative (`### The 7 Expert Evaluators`,
  "Available Experts" bullet list, and various "7-expert committee" references) predates both
  `eval-alumni-adversary` and this release's `eval-alumni-codification-judge` and was not updated
  to reflect either - the adversary already shipped in a prior release with the same gap. T-15's
  plan text scoped this release narrowly to the weighting row and Priority Assessment Framework
  entry; a full roster-narrative refresh (renumbering to 9, folding in both personas' descriptions)
  is a separate follow-up, not done here.

## 2.4.8 - 2026-07-29

### Changed
- `skills/eval-scout-generate/SKILL.md` (1.0.0 -> 1.1.0, T-14,
  `eval-committee-deterministic-validators` plan, Phase 4): the fixed
  5-criteria generation template now teaches the deterministic-first model
  the rest of the committee already retrofitted (T-05 through T-13), rather
  than the old quality-bar-only 0-100 scoring for every row.
  - Added a "Classifying each criterion's mode" section that applies T-03's
    rigor bar ("could I write a script that proves this criterion true or
    false", not "does this sound objective") to each of the five generated
    criteria before it is written down, with three concrete outcomes:
    **reuse** an already-classified criterion's real `criterion_id`/
    `check_ids`/`source` from `validators/deterministic_verdict.py`'s
    registry when the generated criterion substantively duplicates one
    (tagged `deterministic`); **new but concretely buildable** (tagged
    `deterministic-pending` with a fresh `[rule_prefix]-[n]` criterion_id
    and a "Deterministic check needed" note carried into the Growth PR
    body for a real follow-up TDD pair); or **genuinely subjective** (no
    tag - the expected default for most criteria on a brand-new domain).
  - The template now includes the same one-time `## Evaluation Criteria`
    legend line the 7 standing alumni carry (per `phase2-rubric-
    annotation-convention.md`), added to every generated evaluator
    regardless of whether any row ends up tagged.
  - New hard rule: never fabricate `check_ids`/`source` values - both must
    trace to a real registry entry (reuse case) or stay blank under
    `deterministic-pending` (new-but-unbuilt case); an invented tag is
    treated as worse than no tag, since it tells Step 4.0 to run a check
    that does not exist.
  - Doc/template-only change - no existing test infrastructure covers this
    skill's generation-template output (confirmed: `tests/` has only
    `test_deterministic_verdict.py`, no eval-scout-generate coverage), so
    no TDD pair was required per this task's own scope.
- README.md: new "`eval-scout-generate`'s deterministic-first template
  (T-14)" subsection under Development & Testing, documenting the same
  change for a reader browsing the plugin's own docs.

## 2.4.7 - 2026-07-29

### Added
- `compute_c_h1_verdict()` added to `validators/deterministic_verdict.py`
  (T-13, `eval-committee-deterministic-validators` plan, Phase 4): the
  FIFTH and LAST criterion in `aios-eval`'s scope, completing T-13 and this
  repo's entire Phase 4 retrofit. Covers C-H1 "Technical Correctness" (Doc
  Hartwell's Technical Correctness domain).
  - Unlike C-W1/C-R5 (both deliberately scoped down because this repo
    lacks bandit/semgrep/`baseline-findings.json` infrastructure the
    ai-os-jc-toast reference routes to), C-H1 needs no infrastructure this
    repo is missing: `ast.parse()` is Python's own stdlib parser and
    `bash -n` is bash's own built-in syntax-only parse mode - both
    zero-install. Confirmed directly present in THIS repo's own
    environment before writing anything (`python3 -c "import ast"`
    succeeds; `bash -n` runs clean here too) - so this is a **faithful
    full port** of ai-os-jc-toast's language-detection + multi-toolchain-
    dispatch shape, not a scoped-down reimplementation like C-W1/C-R5.
  - Detects the artifact's language by file extension: `.py` -> `ast.parse()`
    (`H1-PY-SYNTAX`, FAIL with cited line on a `SyntaxError`), `.sh` ->
    `bash -n` over stdin (`H1-SH-SYNTAX`). Every other extension (`.md`,
    `.txt`, `.json`, no extension) resolves `N/A` - per
    `criteria-classification.md`'s own "applicability gap, not
    subjectivity" framing. N/A is the **common** case for this criterion,
    not the rare edge, since every real artifact in this plugin
    (`agents/*.md`, `skills/*/SKILL.md`) is prose.
  - `check_ids` always lists both toolchain IDs regardless of which one
    actually ran, matching every other criterion's own convention here.
  - `tests/test_deterministic_verdict.py` - 8 new tests (Python syntax
    error -> FAIL with cited line, valid Python -> PASS, bash syntax error
    -> FAIL, valid bash -> PASS, prose `.md` artifact -> N/A, unrecognized
    extension (`.json`) -> N/A, `check_ids` always lists both toolchains,
    T-06 output-contract schema conformance). TDD RED (`ImportError:
    cannot import name 'C_H1_CHECK_IDS'`) confirmed before implementation,
    GREEN after - 31/31 passing (23 pre-existing C-W2+C-W1+C-R5+C-N4 + 8
    new). Verified `plugins/memory-os`'s own suite unaffected (69 passed,
    1 pre-existing unrelated failure in `check-memory`'s own frontmatter,
    same baseline as prior T-13 cycles). Smoke-tested against real
    artifacts: `agents/eval-alumni-doc-hartwell.md` (N/A, prose) and
    `validators/deterministic_verdict.py` itself (PASS, valid Python).
  - Scope boundary matches C-W1/C-R5/C-N4's own: only the standalone
    `compute_c_h1_verdict()` callable is exercised - not yet wired into
    `eval/SKILL.md`'s live dispatch. **T-13 is now fully complete** - all
    5 of this repo's deterministic-convertible criteria (C-W2, C-W1, C-R5,
    C-N4, C-H1) have working, tested native implementations.

## 2.4.6 - 2026-07-29

### Added
- `compute_c_n4_verdict()` added to `validators/deterministic_verdict.py`
  (T-13, `eval-committee-deterministic-validators` plan, Phase 4): the
  FOURTH of the remaining 4 criteria (C-W1, C-R5, C-H1, C-N4) - only C-H1
  remains after this cycle. Covers C-N4 "Token Efficiency" (Dr. Nakamura's
  AI Systems domain).
  - Unlike C-W1/C-W2/C-R5 (each routes to or reuses an existing check
    family), C-N4 is the plan's one genuinely NEW check - no existing
    family here wraps token counting, so this module owns the counting
    logic itself, per `criteria-classification.md`'s framing ("exact
    arithmetic... the literal definition of the named metric").
  - **Re-confirmed directly for this repo (not assumed from the
    ai-os-jc-toast reference's own finding)**: no tokenizer library
    (tiktoken or similar) is installed in this repo's Python environment
    either - `python3 -c "import tiktoken"` raises `ModuleNotFoundError`
    here too. `CHARS_PER_TOKEN = 4` (the commonly cited chars/token
    approximation ratio for BPE-family tokenizers) is therefore a
    character-count proxy, not an exact tokenizer count - every evidence
    string this function produces discloses that explicitly rather than
    silently presenting the estimate as exact.
  - **Budget source, also re-confirmed for this repo rather than copied**:
    `DEFAULT_TOKEN_BUDGET = 10_000` reuses THIS repo's own already-
    documented "too long" figure -
    `plugins/skills-toolkit/skills/skills-toolkit/references/agents/
    refactoring-patterns.md` ("Agent exceeds ~10,000 tokens" / "under
    8,000 tokens with no clear redundancy") - not ai-os-jc-toast's copy of
    the same number. The two repos independently converged on the same
    starting default, a useful data point but not the reason this file
    picks 10,000. Flagged as revisable by the eval committee, not a
    platform limit.
  - Counts `artifact.raw` (frontmatter + body combined), not body alone -
    the frontmatter is also loaded into context every time the artifact is
    read as a prompt, so excluding it would understate the real token
    cost. Over-budget rolls up to a hard FAIL (exact arithmetic, not a
    soft/WARN-prone proxy like C-W1's regex family).
  - `tests/test_deterministic_verdict.py` - 6 new tests (under-budget PASS
    with count+threshold in evidence, over-budget FAIL, exact-boundary PASS
    not FAIL, honesty-disclosure of the char-count approximation,
    frontmatter-plus-body-not-body-only counting, T-06 schema conformance).
    TDD RED (`ImportError: cannot import name 'CHARS_PER_TOKEN'`) confirmed
    before implementation, GREEN after - 23/23 passing (17 pre-existing
    C-W2+C-W1+C-R5 + 6 new). Verified `plugins/memory-os`'s own suite
    unaffected (69 passed, 1 pre-existing unrelated failure in
    `check-memory`'s own frontmatter, same baseline as prior T-13 cycles).
  - Scope boundary matches C-W1/C-R5's own: only the standalone
    `compute_c_n4_verdict()` callable is exercised - not yet wired into
    `eval/SKILL.md`'s live dispatch. Remaining in this repo's scope: C-H1.

## 2.4.5 - 2026-07-29

### Added
- `validators/reference_scan.py` (T-13, `eval-committee-deterministic-validators`
  plan, Phase 4): a native, deliberately lightweight dead-markdown-link
  scanner backing a new `compute_c_r5_verdict()` for the C-R5 "Wayfinding &
  Navigation" criterion (Sam Rodriguez's Accessibility & UX Architecture
  domain) - the THIRD of the remaining 4 criteria (C-W1, C-R5, C-H1, C-N4).
  - Confirmed before writing this (not assumed): aios-eval has NO existing
    dead-link/orphan-reference infrastructure - a repo-wide grep for "dead",
    "orphan", "reference" turned up exactly one hit, a CHANGELOG prose
    mention of an external validate-marketplace sweep having fixed "C16
    orphan-reference links" in this plugin's own files at some point, not a
    native check module. Also confirmed: no `baseline-findings.json`/CI
    ratchet mechanism exists anywhere in this repo (zero hits for
    "baseline-findings"/"generated_at").
  - **Single-source, not mixed-source**: unlike ai-os-jc-toast's own C-R5
    (`compute_c_r5_verdict`, T-09), which is genuinely MIXED (a live
    C15-DEAD-REFERENCE scan combined with a C16/C17 baseline-lookup, since
    that repo has a committed CI ratchet file to route the corpus-level
    half to), this native version is SINGLE-source: only the live,
    per-artifact dead-markdown-link check (`C15-DEAD-REFERENCE`). No
    baseline half is invented from scratch here, per this task's own
    explicit instruction - a future baseline-lookup half could be added if
    aios-eval ever gets its own CI ratchet mechanism.
  - **Severity deviation (disclosed)**: uses `Severity.FAIL` for a dead
    link, not the `Severity.WARN` ai-os-jc-toast's own C15-DEAD-REFERENCE
    check uses (that repo downgraded to WARN after a targeted eval found
    FAIL risked false positives across its much larger, more heterogeneous
    corpus). This task's own explicit test specification calls for FAIL, so
    that is what this native version implements - flagged as the natural
    revision point (WARN + a soft-ref-equivalent convention) if the same
    false-positive class is ever observed in this repo's own artifacts.
  - Real markdown link syntax only (`[text](target)`), URL-scheme and
    anchor-only targets skipped, in-file anchors stripped before
    resolution. Relative targets resolve against the artifact's own
    directory first, falling back to its plugin root - mirrors
    ai-os-jc-toast's own resolution order. Deliberately does NOT port
    fenced-code-block/inline-code-span stripping or the `[soft-ref]`
    exemption marker from the ai-os-jc-toast reference - disclosed as a
    known, not-yet-observed false-positive gap in the module's own
    docstring, matching this task's "much simpler...no baseline/corpus-
    level complexity needed" framing for a first native version.
  - `tests/test_deterministic_verdict.py` - 5 new tests (dead link -> FAIL,
    valid link -> PASS, no links -> PASS, external URL/anchor-only links
    ignored, T-06 schema conformance). TDD RED
    (`ImportError: cannot import name 'C_R5_CHECK_IDS'`) confirmed before
    implementation, GREEN after - 17/17 passing. Smoke-tested against all
    13 real `agents/*.md`/`skills/*/SKILL.md` artifacts in this plugin: all
    PASS, including several files with real relative markdown links to
    `templates/*.md` that genuinely resolve - confirming the check
    exercises real link resolution, not a trivial no-links pass.

## 2.4.4 - 2026-07-29

### Added
- `validators/security_scan.py` + `validators/data/security-patterns.json`
  (T-13, `eval-committee-deterministic-validators` plan, Phase 4): a native,
  deliberately lightweight regex-based security anti-pattern scanner backing
  a new `compute_c_w1_verdict()` for the C-W1 "Security Vulnerabilities"
  criterion (Sarah Winters' Security & Trust domain).
  - Unlike C-W2 (a faithful native port of an existing ai-os-jc-toast
    check), this criterion has no upstream counterpart to port:
    ai-os-jc-toast's own `compute_c_w1_verdict` routes to a baseline-lookup
    against a corpus-level bandit/semgrep CI scan - infrastructure this
    repo does not have. Confirmed directly via a repo-wide grep for
    "bandit", "semgrep", and "SEC-" before writing this: zero hits
    anywhere in `ai-os-personal`.
  - Scope decision: rather than building a full bandit/semgrep-backed SAST
    pipeline from scratch for one criterion in one cycle, this follows
    `compute_c_w2_verdict`'s live-artifact-scan shape instead, backed by a
    small, curated regex sweep covering 2 anti-pattern families -
    hardcoded secrets/credentials (`SEC-001`) and dangerous dynamic
    execution/shell injection (`SEC-003`). check_id numbers align with
    ai-os-jc-toast's own `bandit_security.py` catalogue naming for the same
    families (readability only, not a claim of equivalent detection power).
  - **Explicitly out of scope, disclosed in `security_scan.py`'s own
    docstring**: no SQL injection, weak-crypto, path-traversal,
    deserialization, SSRF, or XSS coverage (need AST/taint-flow analysis a
    regex sweep cannot provide with precision); cannot distinguish real
    dangerous code from prose that merely discusses these patterns (e.g. a
    security-education doc saying "avoid eval()" false-positives) - smoke-
    tested against this module's own docstring, which does exactly that,
    confirming the disclosed limitation is real and not hypothetical. All
    6 real `agents/*.md`/`skills/*/SKILL.md` artifacts smoke-tested clean
    (PASS).
  - `tests/test_deterministic_verdict.py` - 7 new tests (hardcoded secret,
    AWS access key ID, eval() call, shell=True subprocess, clean artifact,
    safe-placeholder exemption, T-06 schema conformance). TDD RED
    (`ImportError: cannot import name 'C_W1_CHECK_IDS'`) confirmed before
    implementation, GREEN after - 12/12 passing.
  - Caught and fixed during this cycle's own GREEN run: an early draft
    accidentally named a new test `test_clean_artifact_returns_pass_verdict`,
    identical to an existing C-W2 test - Python's module-level function
    definitions silently let the later one shadow the earlier one, so
    pytest only collected 11 items instead of the expected 12 with no
    error. Renamed to `test_c_w1_clean_artifact_returns_pass_verdict` once
    the mismatched count was noticed.
  - Scope boundary (matches T-12a/b's own): only the standalone
    `compute_c_w1_verdict()` callable is exercised - not yet wired into
    `eval/SKILL.md`'s live dispatch. Remaining after this cycle: C-R5,
    C-H1, C-N4.

## 2.4.3 - 2026-07-29

### Added
- `validators/` - a new native Python/pytest module (T-12a/b,
  `eval-committee-deterministic-validators` plan, Phase 4): the first
  deterministic-convertible criterion (C-W2, Data Privacy & Protection,
  Sarah Winters' domain) ported as an executable pass/fail check rather than
  a purely subjective LLM judgment. Mirrors the `DeterministicVerdict` /
  `VerdictSource` contract and roll-up algorithm already shipped in
  ai-os-jc-toast's `toast-plugin-validator` (T-08a/b) field-for-field, but
  is a native port, not a cross-repo import - aios-eval is a separate
  repo/org and cannot import across repos.
  - `validators/deterministic_verdict.py` - `compute_c_w2_verdict()`,
    `DeterministicVerdict`/`VerdictSource` dataclasses, `roll_up_verdict()`.
  - `validators/pii_scan.py` - native PII regex scan engine (email, phone,
    SSN, credit card, address, name-context, public IP), ported from
    `toast-plugin-validator`'s `c06_pii.py` check.
  - `validators/findings.py`, `validators/artifact.py` - minimal
    Finding/Severity/Artifact data shapes this repo did not have before.
  - `validators/data/pii-patterns.json` - the same regex categories,
    severities, and safe-value exemption lists as the ai-os-jc-toast source,
    copied as data (not imported).
  - `tests/test_deterministic_verdict.py` - 5 tests (FAIL/PASS/WARN-only/
    safe-placeholder-exemption/T-06 schema conformance), TDD RED-then-GREEN.
  - `pyproject.toml` - this plugin's first pytest scaffold (mirrors
    `plugins/memory-os/pyproject.toml`'s existing pattern), since aios-eval
    had zero Python/pytest infrastructure before this change.
  - Scope boundary (deliberate, matches T-08a/b's own): only the standalone
    `compute_c_w2_verdict()` callable is exercised. This does not yet wire
    into `eval/SKILL.md`'s live dispatch - that wiring (mirroring T-10.5) is
    a separate, not-yet-scoped follow-on task.

## 2.4.2 - 2026-07-24

Validator sweep (validate-marketplace sweep, 2026-07-23/24): fixed 33 findings (missing effort: fields, C16 orphan-reference links, dead template deletion, Task tracking gaps, CODIFY triage steps). 14 findings deferred as intentional (persona-schema fields, fictional AI-persona names).

## 2.4.1 - 2026-07-12

### Fixed
- validator sweep (validator-rebuild Wave 9): trimmed 5 agent descriptions over the 250-char
  cap, added missing `TaskGet` to the canonical Task* set on 7 eval-alumni agents, fixed a
  YAML-breaking unescaped quote in `eval-alumni-jack-morrison.md`'s description, fixed a
  YAML-breaking `WHEN NOT:` colon-space pattern and trimmed an oversized description in
  `skills/eval/SKILL.md`, trimmed the oversized description in `skills/eval-scout/SKILL.md`,
  and replaced em dashes with ` - ` throughout both SKILL.md bodies (repo-wide no-em-dash rule).

## 2.4.0 - 2026-06-17

### Added
- Quality-bar upgrade (introduced via #39, version-reconciled here): recentres the committee
  rubric so correct-but-bland lands in the 70s and the 90s must be earned by craft.
  - `references/quality-bar-rubric.md`: the recentred 0-100 bands plus craft/depth/design-POV/
    originality/honest-next-improvement axes. Supersedes the old defect-absence anchors.
  - `agents/eval-alumni-adversary.md`: mandatory adversarial reviewer that finds the worst real
    fault and can cap the committee score (major craft fault -> max 84; oversell -> 84;
    correctness/safety slip -> 69).
  - `skills/eval-scout-generate/`: on-demand evaluator generation under a fixed five-criteria
    template, the library-gap protocol, and PR-upstream growth.
  - `agents/generated/eval-alumni-comic-craft.md`: the first generated evaluator, proving the
    generation path.
  - `QUALITY-BAR-UPGRADE.md`: overview of the change and why it is a craft bar, not gamification.

### Fixed
- `plugin.json` now registers the agents and skill added above (eval-alumni-adversary,
  agents/generated/eval-alumni-comic-craft, eval-scout-generate), which #39 left unregistered.

## 2.3.0 - 2026-03-21

### Added
- eval-scout skill: on-demand scanner that evaluates skills across plugins for promotion to contracted eval alumni members
  - 4-criteria scoring (domain depth, evaluation perspective, testable output, cross-domain reach)
  - Threshold: 60+ for candidacy, ranked report output
  - Feeds into add-eval-member skill (H1 design doc)
- plugin.json: explicitly registered all 8 agents and 2 skills (was missing)

## 2.2.0 - 2026-03-21

### Added
- eval skill: merged 8 commands (orchestrator + 7 persona wrappers) into single AskUserQuestion-driven skill

### Changed
- All 8 agent files: added [AI] tag to every persona name appearance (68 lines)  -  personas are AI, not real people

### Removed
- All 8 command files: eval.md, eval-access.md, eval-ai.md, eval-docs.md, eval-pm.md, eval-practical.md, eval-security.md, eval-tech.md

## 2.1.0 - 2026-02-20

### Changed
- Migrated from TodoWrite to Task* tools across all agents
