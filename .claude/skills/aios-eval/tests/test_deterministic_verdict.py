"""T-12a (eval-committee-deterministic-validators plan, Phase 4): failing test
for the FIRST deterministic-convertible criterion ported natively into
aios-eval (ai-os-personal), C-W2 (Data Privacy & Protection, Sarah Winters'
Security & Trust domain).

Mirrors ai-os-jc-toast's T-08a reference pattern
(plugins/toast-plugin-validator/tests/validators/test_deterministic_verdict.py,
compute_c_w2_verdict tests) field-for-field, but this module is a NATIVE port,
not a cross-repo import - per phase2-mechanism-design.md's Decision 1 ("one
shared contract, two native implementations"), aios-eval lives in a separate
repo/org (github.com/YoungLeadersDotTech) from toast-plugin-validator
(github.toasttab.com) and cannot import across repos.

Why C-W2 again (not a different criterion): criteria-survey-ai-os-personal.md
(T-02) confirms aios-eval's own Sarah Winters agent carries the identical
C-W2 "Data Privacy & Protection" criterion (same persona, same 25% weight,
same description) as ai-os-jc-toast's - Layer C is a near-exact fork between
the two repos. Picking the same criterion keeps the two ports directly
comparable and lets phase2-output-contract.md's pii-patterns.json regex data
carry over with zero adaptation.

Scope boundary (deliberate, per the task): this only exercises the standalone
compute_c_w2_verdict() callable in isolation, same scope boundary T-08a drew -
it does NOT exercise aios-eval's `eval` skill's live Step 4 dispatch (that
wiring, mirroring T-10.5, is out of scope for T-12a/b).
"""
from __future__ import annotations

from pathlib import Path

from validators.artifact import Artifact
from validators.deterministic_verdict import (
    CHARS_PER_TOKEN,
    C_H1_CHECK_IDS,
    C_N4_CHECK_IDS,
    C_R5_CHECK_IDS,
    C_W1_CHECK_IDS,
    C_W2_CHECK_IDS,
    DEFAULT_TOKEN_BUDGET,
    DeterministicVerdict,
    compute_c_h1_verdict,
    compute_c_n4_verdict,
    compute_c_r5_verdict,
    compute_c_w1_verdict,
    compute_c_w2_verdict,
)


def _artifact(body: str, frontmatter: str | None = None) -> Artifact:
    fm = frontmatter if frontmatter is not None else "name: demo-agent\ndescription: x\n"
    raw = f"---\n{fm}---\n{body}"
    return Artifact(path=Path("fake/agents/demo-agent.md"), raw=raw)


def test_pii_found_returns_fail_verdict_with_evidence():
    """A real email in the artifact body must roll up to a hard FAIL verdict,
    per T-06's roll-up algorithm ("any FAIL finding -> FAIL"), reused
    unchanged here."""
    artifact = _artifact("Contact sarah.j@company.com for details.\n")

    verdict = compute_c_w2_verdict(artifact)

    assert isinstance(verdict, DeterministicVerdict)
    assert verdict.verdict == "FAIL"
    assert "C6-PII-EMAIL" in verdict.evidence
    assert "sarah.j@company.com" not in verdict.evidence  # cite check_id/message, never the raw PII


def test_clean_artifact_returns_pass_verdict():
    """No PII patterns anywhere -> PASS, zero findings."""
    artifact = _artifact("This agent has no personal data in its body.\n")

    verdict = compute_c_w2_verdict(artifact)

    assert verdict.verdict == "PASS"
    assert verdict.findings == []


def test_warn_only_finding_still_passes_but_is_visible_in_evidence():
    """A WARN-severity match (a real-looking phone number, outside the
    555-0100..0199 safe test range) must NOT flip the verdict to FAIL - only
    FAIL findings gate the verdict per T-06 Part 1 - but must still be
    visible, non-blocking, in the evidence text."""
    artifact = _artifact("Call 555-987-6543 now.\n")

    verdict = compute_c_w2_verdict(artifact)

    assert verdict.verdict == "PASS"
    assert len(verdict.findings) == 1
    assert verdict.findings[0]["check_id"] == "C6-PII-PHONE"
    assert "C6-PII-PHONE" in verdict.evidence


def test_safe_placeholder_values_are_exempt():
    """Documented-safe placeholders (example.com email, FCC test-range phone,
    publicly-documented test card number) must not be flagged at all -
    mirrors the exemption lists already shipped in pii-patterns.json."""
    artifact = _artifact(
        "Reach out to demo@example.com or call 555-0142. "
        "Test card 4111111111111111 for the sandbox.\n"
    )

    verdict = compute_c_w2_verdict(artifact)

    assert verdict.verdict == "PASS"
    assert verdict.findings == []


def test_verdict_matches_t06_output_contract_schema():
    """Field-for-field check against phase2-output-contract.md Part 1's
    DeterministicVerdict shape - the same contract T-08b satisfied in
    ai-os-jc-toast, now satisfied natively here too."""
    artifact = _artifact("Nothing sensitive here.\n")

    verdict = compute_c_w2_verdict(artifact, computed_at="2026-07-29T00:00:00Z")
    payload = verdict.to_dict()

    assert payload["criterion_id"] == "C-W2"
    assert payload["criterion_label"] == "Data Privacy & Protection"
    assert payload["persona"] == "eval-alumni-sarah-winters"
    assert payload["domain"] == "Security & Trust"
    assert payload["verdict"] in {"PASS", "FAIL", "N/A"}
    assert payload["check_ids"] == C_W2_CHECK_IDS
    assert payload["source"]["mode"] == "live-artifact-scan"
    assert payload["source"]["computed_at"] == "2026-07-29T00:00:00Z"
    assert isinstance(payload["findings"], list)


# ---- T-13: C-W1 (Security Vulnerabilities) -------------------------------
#
# T-13 (eval-committee-deterministic-validators plan, Phase 4, this cycle):
# failing tests for the SECOND deterministic-convertible criterion ported
# natively into aios-eval, C-W1 (Security Vulnerabilities, Sarah Winters'
# Security & Trust domain) - the same criterion ai-os-jc-toast's T-09 added
# via compute_c_w1_verdict (baseline-lookup against bandit/semgrep CI
# output). aios-eval has NO equivalent baseline mechanism - confirmed by a
# repo-wide grep for "bandit", "semgrep", and "SEC-" before writing this
# file: zero hits anywhere in this repo. Rather than building a full
# bandit/semgrep-backed SAST pipeline from scratch for one criterion in one
# cycle (disproportionate scope), this ports the shape of compute_c_w2_verdict
# instead (a live-artifact-scan), backed by a new, deliberately lightweight
# native regex module (validators/security_scan.py) covering 2 anti-pattern
# families: hardcoded secrets/credentials (SEC-001) and dangerous dynamic
# execution/shell injection (SEC-003). See security_scan.py's own docstring
# and validators/data/security-patterns.json's "_meta" block for the full
# scope-reduction rationale and known gaps versus ai-os-jc-toast's version.


def test_hardcoded_secret_returns_fail_verdict_with_evidence():
    """A real-looking hardcoded API key assignment must roll up to a hard
    FAIL verdict, and the evidence must cite the check_id/message - never
    the raw secret value itself (mirrors C-W2's own never-quote-the-raw-
    sensitive-text convention)."""
    artifact = _artifact('api_key = "sk-live-9f8a7b6c5d4e3f2a1b0c"\n')

    verdict = compute_c_w1_verdict(artifact)

    assert isinstance(verdict, DeterministicVerdict)
    assert verdict.verdict == "FAIL"
    assert "SEC-001" in verdict.evidence
    assert "sk-live-9f8a7b6c5d4e3f2a1b0c" not in verdict.evidence


def test_aws_access_key_id_returns_fail_verdict():
    """A bare AWS access key ID pattern (AKIA...) must be caught even
    without a surrounding key=value assignment - it is unambiguous by
    format alone."""
    artifact = _artifact("Old creds still in history: AKIAABCDEFGHIJKLMNOP\n")

    verdict = compute_c_w1_verdict(artifact)

    assert verdict.verdict == "FAIL"
    assert "SEC-001" in verdict.evidence


def test_eval_call_returns_fail_verdict():
    """Dangerous dynamic execution (eval/exec) must roll up to FAIL under
    SEC-003 - the shell-injection/eval family, per
    validators/data/security-patterns.json's naming rationale."""
    artifact = _artifact("result = eval(user_supplied_expression)\n")

    verdict = compute_c_w1_verdict(artifact)

    assert verdict.verdict == "FAIL"
    assert "SEC-003" in verdict.evidence


def test_shell_true_subprocess_call_returns_fail_verdict():
    """subprocess.*(..., shell=True) is the classic shell-injection vector -
    same SEC-003 family as eval/exec, per the bandit_security.py mapping
    table this check's naming aligns with."""
    artifact = _artifact('subprocess.run(f"rm {user_path}", shell=True)\n')

    verdict = compute_c_w1_verdict(artifact)

    assert verdict.verdict == "FAIL"
    assert "SEC-003" in verdict.evidence


def test_c_w1_clean_artifact_returns_pass_verdict():
    """No security anti-patterns anywhere -> PASS, zero findings. Named
    distinctly from C-W2's own test_clean_artifact_returns_pass_verdict
    above - an earlier draft of this test accidentally reused that exact
    name, which silently shadowed the C-W2 test at module-import time
    (Python just keeps the later of two same-named top-level functions),
    dropping it from collection with no error. Caught by an unexpected
    11-vs-12 collected-test count during this cycle's own GREEN run;
    renamed here so both tests actually run."""
    artifact = _artifact("This agent evaluates code quality and style.\n")

    verdict = compute_c_w1_verdict(artifact)

    assert verdict.verdict == "PASS"
    assert verdict.findings == []


def test_safe_placeholder_secret_is_exempt():
    """A documentation-style placeholder value (obvious instructional
    stand-in, not a real secret) must not be flagged - mirrors C-W2's own
    safe-value exemption pattern."""
    artifact = _artifact('Set your credential: api_key = "YOUR_API_KEY_HERE"\n')

    verdict = compute_c_w1_verdict(artifact)

    assert verdict.verdict == "PASS"
    assert verdict.findings == []


def test_c_w1_verdict_matches_t06_output_contract_schema():
    """Field-for-field check against phase2-output-contract.md Part 1's
    DeterministicVerdict shape, same schema check T-12a ran for C-W2."""
    artifact = _artifact("Nothing dangerous here.\n")

    verdict = compute_c_w1_verdict(artifact, computed_at="2026-07-29T00:00:00Z")
    payload = verdict.to_dict()

    assert payload["criterion_id"] == "C-W1"
    assert payload["criterion_label"] == "Security Vulnerabilities"
    assert payload["persona"] == "eval-alumni-sarah-winters"
    assert payload["domain"] == "Security & Trust"
    assert payload["verdict"] in {"PASS", "FAIL", "N/A"}
    assert payload["check_ids"] == C_W1_CHECK_IDS
    assert payload["source"]["mode"] == "live-artifact-scan"
    assert payload["source"]["computed_at"] == "2026-07-29T00:00:00Z"
    assert isinstance(payload["findings"], list)


# ---- T-13: C-R5 (Wayfinding & Navigation) ---------------------------------
#
# T-13 (eval-committee-deterministic-validators plan, Phase 4, THIRD of the
# remaining 4 criteria): failing tests for C-R5 (Wayfinding & Navigation,
# Sam Rodriguez's Accessibility & UX Architecture domain) - the SAME
# criterion ai-os-jc-toast's T-09 added via compute_c_r5_verdict, but this
# native aios-eval version is deliberately SINGLE-source (a live markdown-
# link-vs-on-disk-file scan only), NOT mixed live+baseline like the
# ai-os-jc-toast reference. Confirmed by a repo-wide grep for
# "baseline-findings"/"generated_at" before writing this file: zero hits
# anywhere in aios-eval - there is no CI ratchet mechanism here to route a
# C16/C17-equivalent corpus-level half to, and per this task's own explicit
# instruction, one is not invented from scratch just to mirror
# ai-os-jc-toast's shape. See validators/reference_scan.py's own docstring
# for the full single-vs-mixed-source rationale.
#
# These tests deliberately do NOT reuse the shared _artifact() helper above
# (which builds a fake, non-existent "fake/agents/demo-agent.md" path) -
# unlike the regex-only PII/security scans, this criterion's check touches
# the real filesystem (does the linked file actually exist on disk), so its
# fixtures need a real tmp_path-backed directory tree instead.
#
# Severity choice, a deliberate disclosed DEVIATION from the ai-os-jc-toast
# reference: that repo's C15-DEAD-REFERENCE check uses Severity.WARN (a
# targeted eval there found FAIL risked false positives across a much
# larger, more heterogeneous corpus). This native version uses Severity.FAIL
# instead, per this task's own explicit test specification ("an artifact
# with a dead link -> FAIL") - see reference_scan.py's own docstring for
# the full rationale.


def _make_agent_artifact(tmp_path, body: str, plugin_name: str = "aios-eval") -> Artifact:
    """Real on-disk fixture: <tmp_path>/plugins/<plugin_name>/agents/demo-agent.md.
    Mirrors this repo's actual plugin layout so plugin-root fallback
    resolution (own dir first, then plugin root) is exercised faithfully,
    not just approximated with a fake unrooted path."""
    agent_dir = tmp_path / "plugins" / plugin_name / "agents"
    agent_dir.mkdir(parents=True, exist_ok=True)
    raw = f"---\nname: demo-agent\ndescription: x\n---\n{body}"
    return Artifact(path=agent_dir / "demo-agent.md", raw=raw)


def test_dead_link_returns_fail_verdict(tmp_path):
    """A markdown link whose target file does not exist anywhere (own dir
    or plugin root) must roll up to a hard FAIL verdict - per this task's
    own explicit test specification, a deliberate deviation from
    ai-os-jc-toast's WARN choice for the same check_id (see
    reference_scan.py's own docstring for why)."""
    artifact = _make_agent_artifact(tmp_path, "See [ghost](./nowhere.md) for details.\n")

    verdict = compute_c_r5_verdict(artifact)

    assert isinstance(verdict, DeterministicVerdict)
    assert verdict.verdict == "FAIL"
    assert "C15-DEAD-REFERENCE" in verdict.evidence
    assert verdict.findings[0]["check_id"] == "C15-DEAD-REFERENCE"
    assert verdict.findings[0]["severity"] == "FAIL"


def test_valid_link_returns_pass_verdict(tmp_path):
    """A markdown link whose target file genuinely exists on disk (relative
    to the artifact's own directory) must not be flagged at all."""
    artifact = _make_agent_artifact(tmp_path, "See [sibling](./sibling.md) for details.\n")
    (artifact.path.parent / "sibling.md").write_text("# Sibling\n")

    verdict = compute_c_r5_verdict(artifact)

    assert verdict.verdict == "PASS"
    assert verdict.findings == []


def test_no_links_returns_pass_verdict_with_zero_findings(tmp_path):
    """An artifact with no markdown links at all has nothing to fail on -
    PASS, zero findings, same convention as C-W2/C-W1's own clean-artifact
    tests."""
    artifact = _make_agent_artifact(tmp_path, "Nothing linked here.\n")

    verdict = compute_c_r5_verdict(artifact)

    assert verdict.verdict == "PASS"
    assert verdict.findings == []


def test_external_url_and_anchor_only_links_are_not_checked(tmp_path):
    """A real http(s) URL and a same-page anchor-only link are not local
    file references at all - never checked for on-disk existence, never
    flagged."""
    artifact = _make_agent_artifact(
        tmp_path,
        "See [docs](https://example.com/docs) and [top](#top) for details.\n",
    )

    verdict = compute_c_r5_verdict(artifact)

    assert verdict.verdict == "PASS"
    assert verdict.findings == []


def test_c_r5_verdict_matches_t06_output_contract_schema(tmp_path):
    """Field-for-field check against phase2-output-contract.md Part 1's
    DeterministicVerdict shape, same schema check T-12a/T-13 ran for
    C-W2/C-W1. source.mode is "live-artifact-scan" here (single-source),
    NOT "mixed-live-and-baseline" like ai-os-jc-toast's own C-R5 - the
    single-vs-mixed-source distinction this task's design decision made."""
    artifact = _make_agent_artifact(tmp_path, "Nothing linked here.\n")

    verdict = compute_c_r5_verdict(artifact, computed_at="2026-07-29T00:00:00Z")
    payload = verdict.to_dict()

    assert payload["criterion_id"] == "C-R5"
    assert payload["criterion_label"] == "Wayfinding & Navigation"
    assert payload["persona"] == "eval-alumni-sam-rodriguez"
    assert payload["domain"] == "Accessibility & UX Architecture"
    assert payload["verdict"] in {"PASS", "FAIL", "N/A"}
    assert payload["check_ids"] == C_R5_CHECK_IDS
    assert payload["source"]["mode"] == "live-artifact-scan"
    assert payload["source"]["computed_at"] == "2026-07-29T00:00:00Z"
    assert isinstance(payload["findings"], list)


# ---- T-13: C-N4 (Token Efficiency) ----------------------------------------
#
# T-13 (eval-committee-deterministic-validators plan, Phase 4, FOURTH of the
# remaining 4 criteria - LAST one this cycle; C-H1 remains after this):
# failing tests for C-N4 (Token Efficiency, Dr. Nakamura's AI Systems
# domain) - the SAME criterion ai-os-jc-toast's T-09 added via
# compute_c_n4_verdict. Mirrors that reference test shape field-for-field
# (test names, budget-boundary behaviour, honesty-disclosure assertion),
# adapted to this repo's own _artifact() helper (now takes an optional
# frontmatter= override so the frontmatter-vs-body-only test below can
# grow the frontmatter independently of the body, the same thing the
# ai-os-jc-toast reference's own _artifact() helper supports).
#
# Unlike C-W1/C-W2/C-R5 (each routes to or reuses an existing check
# family - PII regex, security regex, dead-link scan), C-N4 is the plan's
# one genuinely NEW check: there is no existing check family here to wrap,
# this module owns the counting logic itself (same framing as the
# ai-os-jc-toast reference's own docstring).
#
# Two things re-confirmed directly for THIS repo, not assumed from the
# ai-os-jc-toast reference's findings (per this task's own instruction):
#
# 1. tiktoken (or any other real tokenizer) is NOT installed in this
#    repo's Python environment either - confirmed via `python3 -c "import
#    tiktoken"` -> ModuleNotFoundError, run fresh against THIS repo's
#    interpreter, not copied from the other repo's finding. CHARS_PER_TOKEN
#    = 4 remains a character-count approximation, not an exact tokenizer
#    count, and the evidence text says so explicitly (same honesty
#    requirement the ai-os-jc-toast reference already satisfies).
# 2. This repo has its OWN documented "too long" token-budget guidance,
#    independent of ai-os-jc-toast's copy: `plugins/skills-toolkit/skills/
#    skills-toolkit/references/agents/refactoring-patterns.md` ("Agent
#    exceeds 10,000 tokens" / "under 8,000 tokens with no clear
#    redundancy"). DEFAULT_TOKEN_BUDGET = 10_000 here reuses THIS repo's
#    own already-agreed number, not a copy of the other repo's constant -
#    the two repos independently converged on the same figure, which is
#    itself a useful data point but not the reason this file picks 10,000.


def test_under_budget_artifact_is_pass_with_count_and_threshold_in_evidence():
    """A small artifact, well under the default 10,000-token budget, must
    roll up to PASS - and the evidence string must still name the actual
    character count and the budget threshold (T-06's requirement: evidence
    states the actual count + threshold + PASS/FAIL, not just a bare
    verdict)."""
    artifact = _artifact("A short, unremarkable skill body.\n")
    expected_chars = len(artifact.raw)

    verdict = compute_c_n4_verdict(artifact)

    assert verdict.verdict == "PASS"
    assert str(expected_chars) in verdict.evidence
    assert str(DEFAULT_TOKEN_BUDGET) in verdict.evidence


def test_over_budget_artifact_is_fail_verdict():
    """An artifact whose estimated token count exceeds a (test-supplied,
    small) budget must roll up to a hard FAIL - C-N4 is exact arithmetic,
    not a soft/WARN-only proxy like C-W1's regex family."""
    artifact = _artifact("x" * 400)  # comfortably >10 tokens at 4 chars/token

    verdict = compute_c_n4_verdict(artifact, budget_tokens=10)

    assert verdict.verdict == "FAIL"
    assert len(verdict.findings) == 1
    assert verdict.findings[0]["check_id"] == "N4-TOKEN-BUDGET"
    assert verdict.findings[0]["severity"] == "FAIL"
    assert "N4-TOKEN-BUDGET" in verdict.evidence
    assert "10" in verdict.evidence  # the budget supplied


def test_exact_boundary_at_budget_is_still_pass_not_fail():
    """token_estimate == budget_tokens must be PASS - only strictly
    exceeding the budget is a FAIL (">" not ">="), matching this module's
    hard-line-but-precise arithmetic convention."""
    artifact = _artifact("y" * 40)  # 4 chars/token * 10 tokens = 40 chars exactly
    expected_chars = len(artifact.raw)
    expected_tokens = -(-expected_chars // CHARS_PER_TOKEN)  # ceil division, same formula as SUT

    verdict = compute_c_n4_verdict(artifact, budget_tokens=expected_tokens)

    assert verdict.verdict == "PASS"


def test_evidence_discloses_character_count_approximation_not_exact_tokenizer():
    """No real tokenizer (tiktoken or similar) is installed in THIS repo's
    environment either - re-confirmed directly for aios-eval, not assumed
    from the ai-os-jc-toast finding. The evidence text must say so
    explicitly rather than silently presenting a char-count proxy as an
    exact token count."""
    artifact = _artifact("Some perfectly ordinary skill body text.\n")

    verdict = compute_c_n4_verdict(artifact)

    assert "approxim" in verdict.evidence.lower()
    assert "chars/token" in verdict.evidence or "char" in verdict.evidence.lower()
    assert str(CHARS_PER_TOKEN) in verdict.evidence


def test_prompt_file_is_frontmatter_plus_body_not_body_only():
    """The counted 'prompt file' is artifact.raw (the whole file -
    frontmatter + body), not artifact.body alone - a large frontmatter must
    move the count, proving the function reads .raw and not just the
    body."""
    tiny_body = "x"
    big_frontmatter = "name: demo-agent\ndescription: " + ("z" * 300) + "\n"
    small_fm_artifact = _artifact(tiny_body)
    big_fm_artifact = _artifact(tiny_body, frontmatter=big_frontmatter)

    small_verdict = compute_c_n4_verdict(small_fm_artifact)
    big_verdict = compute_c_n4_verdict(big_fm_artifact)

    assert str(len(small_fm_artifact.raw)) in small_verdict.evidence
    assert str(len(big_fm_artifact.raw)) in big_verdict.evidence
    assert len(big_fm_artifact.raw) > len(small_fm_artifact.raw)


def test_c_n4_verdict_matches_t06_output_contract_schema():
    """Field-for-field check against phase2-output-contract.md Part 1's
    DeterministicVerdict shape - the last of T-13's criteria to satisfy it
    this cycle. source.mode is "live-artifact-scan" (computed fresh from
    the artifact every call, same family as C-W2/C-W1/C-R5's mode here -
    no baseline involved)."""
    artifact = _artifact("Nothing remarkable.\n")

    verdict = compute_c_n4_verdict(artifact, computed_at="2026-07-29T00:00:00Z")
    payload = verdict.to_dict()

    assert payload["criterion_id"] == "C-N4"
    assert payload["criterion_label"] == "Token Efficiency"
    assert payload["persona"] == "eval-alumni-dr-nakamura"
    assert payload["domain"] == "AI Systems"
    assert payload["verdict"] in {"PASS", "FAIL", "N/A"}
    assert payload["check_ids"] == C_N4_CHECK_IDS
    assert payload["source"]["mode"] == "live-artifact-scan"
    assert payload["source"]["computed_at"] == "2026-07-29T00:00:00Z"
    assert isinstance(payload["findings"], list)


# ---- T-13: C-H1 (Technical Correctness) -- LAST of the 4 remaining criteria --
#
# T-13 (eval-committee-deterministic-validators plan, Phase 4, FIFTH and
# LAST criterion overall in aios-eval's scope - only C-H1 remains after
# C-W2/T-12a-b, and C-W1/C-R5/C-N4/T-13): failing tests for C-H1 (Technical
# Correctness, Doc Hartwell's Technical Correctness domain) - the SAME
# criterion ai-os-jc-toast's T-09 added via compute_c_h1_verdict
# (plugins/toast-plugin-validator/validators/deterministic_verdict.py).
#
# Unlike C-W1/C-R5 above (both deliberately SCOPED DOWN here because this
# repo lacks bandit/semgrep/baseline-findings.json infrastructure the
# ai-os-jc-toast reference routes to), C-H1 needs NO infrastructure this
# repo is missing: ast.parse() is Python's own stdlib parser (zero install,
# already usable in any Python 3 environment) and `bash -n` is bash's own
# built-in syntax-only parse mode (zero install, ships with bash itself).
# Confirmed directly for THIS repo's own environment before writing
# anything (not assumed from the ai-os-jc-toast finding): `python3 -c
# "import ast"` succeeds, and `bash -n <<< 'echo hi'` runs clean here too -
# so this is a FAITHFUL FULL PORT of the ai-os-jc-toast reference's
# language-detection + multi-toolchain-dispatch shape, not a scoped-down
# native reimplementation like C-W1/C-R5 had to be.
#
# Per criteria-classification.md's own framing: "'syntax accuracy' and
# 'type safety' are not proxied by a compiler/type-checker/linter - they
# are literally what those terms mean... Scope note: N/A... for prose
# SKILL.md/agent .md artifacts, which is the majority case here - that's
# an applicability gap, not subjectivity." Every artifact this plugin's
# own agents/*.md and skills/*/SKILL.md files represent is prose - so N/A
# is the COMMON case for this criterion, not the rare edge, exactly as the
# ai-os-jc-toast reference's own test suite already established.
#
# `shellcheck` was considered and deliberately NOT used, same reasoning the
# ai-os-jc-toast reference already documented: it would be a real,
# avoidable external-binary dependency for a pytest-covered function, with
# no guarantee of being present in every environment this suite runs in.
# `bash -n` needs no such guard - it IS bash, and bash is already this
# suite's own execution environment.


def _code_artifact(source: str, path_str: str) -> Artifact:
    """C-H1's own fixture - unlike _artifact()'s frontmatter-wrapped prose
    shape (used by C-W2/C-W1/C-N4's tests) or _make_agent_artifact()'s
    on-disk .md fixture (used by C-R5's tests), this builds an Artifact
    whose .raw IS the literal source text of a .py/.sh file - matching
    aios-eval's own minimal Artifact(path, raw) shape (validators/
    artifact.py), which has no frontmatter/body split to begin with. A
    faithful stand-in for a real disk-loaded code artifact, not a special
    case."""
    return Artifact(path=Path(path_str), raw=source)


def test_python_syntax_error_returns_fail_verdict_with_cited_line():
    """A .py artifact with a genuine syntax error must roll up to a hard
    FAIL, and the evidence must cite the offending line number - per
    criteria-classification.md's own "FAIL with cited line" requirement."""
    artifact = _code_artifact(
        "def broken(:\n    pass\n", "plugins/demo/scripts/broken.py",
    )

    verdict = compute_c_h1_verdict(artifact)

    assert isinstance(verdict, DeterministicVerdict)
    assert verdict.verdict == "FAIL"
    assert verdict.findings[0]["check_id"] == "H1-PY-SYNTAX"
    assert "line 1" in verdict.evidence


def test_valid_python_file_returns_pass_verdict():
    """A syntactically valid .py artifact must roll up to PASS - zero
    syntax errors from ast.parse()."""
    artifact = _code_artifact(
        "def greet():\n    return 'hi'\n", "plugins/demo/scripts/greet.py",
    )

    verdict = compute_c_h1_verdict(artifact)

    assert verdict.verdict == "PASS"


def test_bash_syntax_error_returns_fail_verdict():
    """A .sh artifact with a genuine syntax error (unterminated if block)
    must roll up to a hard FAIL via `bash -n`."""
    artifact = _code_artifact(
        "if [ 1 -eq 1 ]; then\n  echo hi\n", "plugins/demo/scripts/broken.sh",
    )

    verdict = compute_c_h1_verdict(artifact)

    assert verdict.verdict == "FAIL"
    assert verdict.findings[0]["check_id"] == "H1-SH-SYNTAX"


def test_valid_bash_file_returns_pass_verdict():
    """A syntactically valid .sh artifact must roll up to PASS via
    `bash -n`."""
    artifact = _code_artifact(
        "if [ 1 -eq 1 ]; then\n  echo hi\nfi\n", "plugins/demo/scripts/ok.sh",
    )

    verdict = compute_c_h1_verdict(artifact)

    assert verdict.verdict == "PASS"


def test_prose_markdown_artifact_is_na_not_scored():
    """A prose SKILL.md/agent .md artifact is the MAJORITY case for this
    criterion's real universe of artifacts in this plugin (all
    eval-committee agents/skills are .md) - per
    criteria-classification.md's own framing, this is N/A (an
    applicability gap), never PASS or FAIL, and never silently treated as
    a subjective judgment call."""
    artifact = _artifact("Just an ordinary skill body, no code here.\n")

    verdict = compute_c_h1_verdict(artifact)

    assert verdict.verdict == "N/A"
    assert verdict.findings == []
    assert "N/A" in verdict.evidence
    assert "scope" in verdict.evidence.lower() or "applicability" in verdict.evidence.lower()


def test_unrecognized_extension_is_also_na():
    """An artifact whose path has no recognized code extension (e.g. a
    bare .json reference file) must also resolve N/A - the detection is by
    extension, not by a blanket 'is this a .md' check."""
    artifact = _code_artifact('{"key": "value"}\n', "plugins/demo/data.json")

    verdict = compute_c_h1_verdict(artifact)

    assert verdict.verdict == "N/A"
    assert verdict.findings == []


def test_c_h1_check_ids_always_list_both_toolchains_regardless_of_language():
    """check_ids reflects the full declared check family for this
    criterion, not just whichever toolchain actually ran for this one
    artifact - matching every other criterion's own precedent here (e.g.
    compute_c_w2_verdict always reports all 7 C6-PII-* ids even when only
    one fired)."""
    artifact = _code_artifact("x = 1\n", "plugins/demo/scripts/tiny.py")

    verdict = compute_c_h1_verdict(artifact)

    assert verdict.check_ids == C_H1_CHECK_IDS
    assert "H1-PY-SYNTAX" in C_H1_CHECK_IDS
    assert "H1-SH-SYNTAX" in C_H1_CHECK_IDS


def test_c_h1_verdict_matches_t06_output_contract_schema():
    """Field-for-field check against phase2-output-contract.md Part 1's
    DeterministicVerdict shape - the LAST of aios-eval's 5 criteria to
    satisfy it, completing T-13."""
    artifact = _code_artifact(
        "def ok():\n    return True\n", "plugins/demo/scripts/ok.py",
    )

    verdict = compute_c_h1_verdict(artifact, computed_at="2026-07-29T00:00:00Z")
    payload = verdict.to_dict()

    assert payload["criterion_id"] == "C-H1"
    assert payload["criterion_label"] == "Technical Correctness"
    assert payload["persona"] == "eval-alumni-doc-hartwell"
    assert payload["domain"] == "Technical Correctness"
    assert payload["verdict"] in {"PASS", "FAIL", "N/A"}
    assert payload["check_ids"] == C_H1_CHECK_IDS
    assert payload["source"]["mode"] == "live-artifact-scan"
    assert payload["source"]["computed_at"] == "2026-07-29T00:00:00Z"
    assert isinstance(payload["findings"], list)
