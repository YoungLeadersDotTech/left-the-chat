"""Deterministic-check bridge for aios-eval (ai-os-personal), Phase 4 of
builder-plans/eval-committee-deterministic-validators--2026-07-26/ (that plan
doc lives in the ai-os-jc-toast repo; this module is this plan's Phase 4
deliverable, native to aios-eval).

Per phase2-mechanism-design.md's Decision 1 ("one shared contract, two native
implementations"): this module reproduces the SAME DeterministicVerdict /
VerdictSource contract and roll-up algorithm that
plugins/toast-plugin-validator/validators/deterministic_verdict.py
(ai-os-jc-toast, T-08b/T-09) implements - field-for-field identical shape,
per phase2-output-contract.md Part 1 - but does not import that module.
aios-eval is a separate repo/org (github.com/YoungLeadersDotTech vs.
github.toasttab.com), confirmed via `git remote -v`, a concrete cross-repo-
import blocker per that same design doc.

Scope (T-12a/b, Phase 4): C-W2 (Data Privacy & Protection) is the first
deterministic-convertible criterion ported here, mirroring T-08a/b's own
starting choice in ai-os-jc-toast - criteria-survey-ai-os-personal.md (T-02)
confirms aios-eval's Sarah Winters agent carries the identical C-W2 criterion
(same persona, same weight, same description), so the port needs zero
adaptation to the criterion definition itself, only to the check-execution
plumbing (this repo's own minimal Artifact/Finding/pii_scan, not
toast-plugin-validator's CheckRegistry).

T-13 (previous cycle) added C-W1 (Security Vulnerabilities) - the second of
the remaining 4 criteria (C-W1, C-R5, C-H1, C-N4). Unlike C-W2 (a faithful
native port of an existing ai-os-jc-toast check), C-W1 has no upstream
check to port: ai-os-jc-toast's own compute_c_w1_verdict routes to a
baseline-lookup against a corpus-level bandit/semgrep CI scan
(baseline-findings.json) - infrastructure this repo does not have,
confirmed via a repo-wide grep for "bandit"/"semgrep"/"SEC-" before writing
this (zero hits). Rather than building a full SAST pipeline from scratch
for one criterion in one cycle, compute_c_w1_verdict here follows
compute_c_w2_verdict's shape instead (live-artifact-scan), backed by a new,
deliberately lightweight native regex module (validators/security_scan.py)
- see that module's own docstring for the full scope-reduction rationale
and known gaps versus ai-os-jc-toast's bandit/semgrep-backed version.

T-13 (previous cycle) added C-R5 (Wayfinding & Navigation) - the third of
the remaining 4 criteria. Unlike ai-os-jc-toast's own compute_c_r5_verdict
(T-09), which is genuinely MIXED-source (a live C15-DEAD-REFERENCE scan
combined with a C16/C17 baseline-lookup, because that repo already has a
committed baseline-findings.json CI ratchet mechanism to route the
corpus-level half to), this native version is SINGLE-source: only the
live, per-artifact dead-markdown-link half, backed by a new native module
(validators/reference_scan.py) - confirmed via a repo-wide grep for
"baseline-findings"/"generated_at" before writing this (zero hits anywhere
in this repo), so no baseline mechanism exists to route a C16/C17-
equivalent half to, and per this task's own explicit instruction one is
not invented from scratch just to mirror ai-os-jc-toast's shape. See
reference_scan.py's own docstring for the full single-vs-mixed-source
rationale and its disclosed FAIL-vs-WARN severity deviation from the
ai-os-jc-toast reference.

T-13 added C-N4 (Token Efficiency) - the FOURTH of the remaining 4
criteria. Unlike C-W1/C-W2/C-R5 (each routes to or reuses an existing
check family), C-N4 is the plan's one genuinely NEW check - no existing
check family here wraps token counting, so this module owns the counting
logic itself, per criteria-classification.md's own framing ("exact
arithmetic... not a proxy, the literal definition of the named metric").

Two things re-confirmed directly for THIS repo (not assumed from the
ai-os-jc-toast reference's own findings), per this task's own instruction:

1. No tokenizer library (tiktoken or similar) is installed in this
   repo's Python environment either - confirmed via `python3 -c "import
   tiktoken"` -> ModuleNotFoundError, run fresh against this repo's own
   interpreter. CHARS_PER_TOKEN = 4 (the commonly cited approximation
   ratio for English-language text with common BPE-family tokenizers,
   including Claude's and GPT's) is therefore a character-count proxy,
   not an exact tokenizer count - every evidence string this produces
   says so explicitly.
2. This repo has its OWN documented "too long" token-budget guidance,
   independent of ai-os-jc-toast's copy: `plugins/skills-toolkit/skills/
   skills-toolkit/references/agents/refactoring-patterns.md` ("Agent
   exceeds 10,000 tokens" / "under 8,000 tokens with no clear
   redundancy"). DEFAULT_TOKEN_BUDGET = 10_000 reuses THIS repo's own
   already-agreed number - the two repos independently converged on the
   same figure, a useful data point, not the reason this file picks it.
   Flagged as a STARTING DEFAULT the eval committee can revise, not a
   settled platform limit.

T-13 (this cycle) adds C-H1 (Technical Correctness) - the FIFTH and LAST
criterion in aios-eval's scope, completing T-13 and this repo's Phase 4
retrofit entirely. Unlike C-W1/C-R5 above (both deliberately SCOPED DOWN
because this repo lacks bandit/semgrep/baseline-findings.json
infrastructure the ai-os-jc-toast reference routes to), C-H1 needs NO
infrastructure this repo is missing: ast.parse() is Python's own stdlib
parser and `bash -n` is bash's own built-in syntax-only parse mode - both
zero-install, confirmed directly present in this repo's own environment
before writing anything (`python3 -c "import ast"` succeeds; `bash -n`
runs clean here too). So this is a FAITHFUL FULL PORT of the
ai-os-jc-toast reference's language-detection + multi-toolchain-dispatch
shape (T-09's compute_c_h1_verdict), not a scoped-down reimplementation
like C-W1/C-R5 had to be. Every other extension (.md, .txt, .json, no
extension) resolves N/A - per criteria-classification.md's own explicit
"applicability gap, not subjectivity" framing - and N/A is the COMMON case
here, not the rare edge, since every real artifact this plugin's own
agents/*.md and skills/*/SKILL.md files represent is prose.
"""
from __future__ import annotations

import ast
import math
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from validators.artifact import Artifact
from validators.findings import Finding, Severity
from validators.pii_scan import scan_pii
from validators.reference_scan import scan_references
from validators.security_scan import scan_security

# C-W2's check_ids - identical set to ai-os-jc-toast's C_W2_CHECK_IDS
# (plugins/toast-plugin-validator/validators/deterministic_verdict.py), per
# phase2-output-contract.md's routing table. Not invented ad hoc here.
C_W2_CHECK_IDS = [
    "C6-PII-EMAIL", "C6-PII-PHONE", "C6-PII-SSN", "C6-PII-CREDIT-CARD",
    "C6-PII-ADDRESS", "C6-PII-NAME-CONTEXT", "C6-PII-IP",
]


@dataclass(frozen=True)
class VerdictSource:
    mode: str  # "live-artifact-scan" | "baseline-lookup"
    detail: str
    computed_at: str


@dataclass(frozen=True)
class DeterministicVerdict:
    """Per phase2-output-contract.md Part 1 - one instance per (criterion,
    artifact) pair. Field-for-field identical to the ai-os-jc-toast shape."""

    criterion_id: str
    criterion_label: str
    persona: str
    domain: str
    verdict: str  # "PASS" | "FAIL" | "N/A"
    evidence: str
    check_ids: list
    source: VerdictSource
    findings: list  # list[dict] - Finding.to_dict() entries

    def to_dict(self) -> dict:
        return {
            "criterion_id": self.criterion_id,
            "criterion_label": self.criterion_label,
            "persona": self.persona,
            "domain": self.domain,
            "verdict": self.verdict,
            "evidence": self.evidence,
            "check_ids": self.check_ids,
            "source": {
                "mode": self.source.mode,
                "detail": self.source.detail,
                "computed_at": self.source.computed_at,
            },
            "findings": self.findings,
        }


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def roll_up_verdict(findings: list, applies: bool = True) -> str:
    """Verdict roll-up algorithm, verbatim per phase2-output-contract.md
    Part 1 - identical to ai-os-jc-toast's roll_up_verdict() so the rule
    cannot drift between the two native implementations."""
    if not applies:
        return "N/A"
    if findings and all(f.severity == Severity.UNTESTED for f in findings):
        return "N/A"
    if any(f.severity == Severity.FAIL for f in findings):
        return "FAIL"
    return "PASS"  # zero findings, or only WARN/INFO (evidence, non-blocking)


def _format_evidence(verdict: str, findings: list) -> str:
    """Human-readable evidence string. FAIL findings are cited by check_id +
    message (never by re-quoting the raw matched PII text, which would leak
    exactly the sensitive data the check exists to catch)."""
    if verdict == "N/A":
        return "N/A - check does not apply to this artifact type."
    fail_findings = [f for f in findings if f.severity == Severity.FAIL]
    if fail_findings:
        return "; ".join(f"{f.check_id}: {f.message}" for f in fail_findings)
    if findings:
        non_blocking = ", ".join(f"{f.check_id} ({f.severity.value})" for f in findings)
        return f"PASS - {len(findings)} non-blocking finding(s): {non_blocking}."
    return "PASS - no findings."


def compute_c_w2_verdict(
    artifact: Artifact, computed_at: Optional[str] = None
) -> DeterministicVerdict:
    """C-W2 Data Privacy & Protection (Sarah Winters, Security & Trust
    domain) - live-artifact-scan via the native pii_scan module.

    T-12a/b's reference implementation: T-13 copies this shape for the
    remaining 4 criteria (C-W1, C-R5, C-H1, C-N4).
    """
    all_findings = scan_pii(artifact)
    findings = [f for f in all_findings if f.check_id in C_W2_CHECK_IDS]

    verdict = roll_up_verdict(findings, applies=True)
    evidence = _format_evidence(verdict, findings)

    return DeterministicVerdict(
        criterion_id="C-W2",
        criterion_label="Data Privacy & Protection",
        persona="eval-alumni-sarah-winters",
        domain="Security & Trust",
        verdict=verdict,
        evidence=evidence,
        check_ids=list(C_W2_CHECK_IDS),
        source=VerdictSource(
            mode="live-artifact-scan",
            detail=f"validators.pii_scan.scan_pii({artifact.path})",
            computed_at=computed_at or _now_iso(),
        ),
        findings=[f.to_dict() for f in findings],
    )


# C-W1's check_ids - a native, lightweight regex family (SEC-001, SEC-003),
# NOT the same 7-id bandit/semgrep-backed set ai-os-jc-toast's C_W1_CHECK_IDS
# names (SEC-001/002/003/004/005/007/008). See validators/security_scan.py
# and validators/data/security-patterns.json for the full scope-reduction
# rationale - this repo has no bandit/semgrep/baseline infrastructure to
# route to (confirmed via repo-wide grep before this was written).
C_W1_CHECK_IDS = ["SEC-001", "SEC-003"]


def compute_c_w1_verdict(
    artifact: Artifact, computed_at: Optional[str] = None
) -> DeterministicVerdict:
    """C-W1 Security Vulnerabilities (Sarah Winters, Security & Trust
    domain) - live-artifact-scan via the native security_scan module.

    Deliberately scoped down vs. ai-os-jc-toast's own compute_c_w1_verdict
    (T-09, toast-plugin-validator): that implementation routes to a
    baseline-lookup against a corpus-level bandit/semgrep CI scan, because
    that repo already has bandit/semgrep as a real, running dependency and
    a committed baseline-findings.json ratchet file. aios-eval has neither
    - confirmed directly (not assumed) via a repo-wide grep for "bandit",
    "semgrep", and "SEC-" prior to writing this function: zero hits
    anywhere in this repo. Building a full SAST pipeline (scanner
    dependency + corpus-level CI job + baseline ratchet) from scratch for
    one criterion in one cron cycle would be disproportionate scope for
    this task.

    Architecturally this follows compute_c_w2_verdict's shape instead
    (live-artifact-scan over artifact.raw, same as the PII check) rather
    than a baseline-lookup - the only shape available without inventing
    corpus-level CI infrastructure this repo doesn't have. The check itself
    (validators/security_scan.py) is a small, curated regex sweep for 2
    anti-pattern families - hardcoded secrets/credentials (SEC-001) and
    dangerous dynamic execution/shell injection (SEC-003) - explicitly NOT
    a full bandit/semgrep-equivalent SAST tool. See security_scan.py's own
    docstring for the disclosed known-gaps list (no SQL injection,
    weak-crypto, path-traversal, deserialization, SSRF, or XSS coverage -
    those need AST/taint-flow analysis this lightweight regex approach
    cannot provide with any precision).
    """
    all_findings = scan_security(artifact)
    findings = [f for f in all_findings if f.check_id in C_W1_CHECK_IDS]

    verdict = roll_up_verdict(findings, applies=True)
    evidence = _format_evidence(verdict, findings)
    evidence = (
        f"{evidence} Source: native regex scan (SEC-001/SEC-003 only) - a "
        f"lightweight anti-pattern sweep, NOT a full bandit/semgrep-backed "
        f"SAST equivalent (this repo has no such infrastructure; see "
        f"security_scan.py for the disclosed scope reduction and known gaps)."
    )

    return DeterministicVerdict(
        criterion_id="C-W1",
        criterion_label="Security Vulnerabilities",
        persona="eval-alumni-sarah-winters",
        domain="Security & Trust",
        verdict=verdict,
        evidence=evidence,
        check_ids=list(C_W1_CHECK_IDS),
        source=VerdictSource(
            mode="live-artifact-scan",
            detail=f"validators.security_scan.scan_security({artifact.path})",
            computed_at=computed_at or _now_iso(),
        ),
        findings=[f.to_dict() for f in findings],
    )


# C-R5's check_ids - a SINGLE native check id (C15-DEAD-REFERENCE), NOT the
# 3-id mixed live+baseline set ai-os-jc-toast's C_R5_CHECK_IDS names
# (C15-DEAD-REFERENCE, C16-ORPHAN-REFERENCE-FILE, C17-CROSS-PLUGIN-FILE-
# REFERENCE). See validators/reference_scan.py for the full single-source-
# vs-mixed-source rationale - this repo has no baseline-findings.json/CI
# ratchet mechanism to route a C16/C17-equivalent corpus-level half to
# (confirmed via a repo-wide grep before this was written: zero hits for
# "baseline-findings" or "generated_at" anywhere in this repo).
C_R5_CHECK_IDS = ["C15-DEAD-REFERENCE"]


def compute_c_r5_verdict(
    artifact: Artifact, computed_at: Optional[str] = None
) -> DeterministicVerdict:
    """C-R5 Wayfinding & Navigation (Sam Rodriguez, Accessibility & UX
    Architecture domain) - live-artifact-scan via the native reference_scan
    module.

    Deliberately scoped down vs. ai-os-jc-toast's own compute_c_r5_verdict
    (T-09, toast-plugin-validator): that implementation is genuinely MIXED-
    source (C15 live + C16/C17 baseline-lookup), because that repo already
    has a committed baseline-findings.json CI ratchet file to route the
    corpus-level half to. aios-eval has neither - confirmed directly (not
    assumed) via a repo-wide grep for "baseline-findings"/"generated_at"
    prior to writing this function: zero hits anywhere in this repo, the
    same absence pattern compute_c_w1_verdict's own docstring already found
    for "bandit"/"semgrep"/"SEC-". Building a baseline/CI-ratchet mechanism
    from scratch for one criterion in one cron cycle, just to mirror
    ai-os-jc-toast's shape, would be disproportionate scope for this task -
    per this task's own explicit instruction not to invent one.

    Architecturally this is SINGLE-source (live-artifact-scan only), the
    same shape compute_c_w2_verdict/compute_c_w1_verdict already use here -
    unlike the mixed-source shape C-R5 takes in ai-os-jc-toast. If aios-eval
    ever gets its own CI ratchet mechanism, a baseline-lookup half (a
    C16/C17-equivalent orphan-reference/cross-plugin-reference check) could
    be added the same way compute_c_w1_verdict's own docstring already
    flags a future baseline-lookup upgrade path for that criterion - not
    built pre-emptively here.

    Severity choice, a deliberate disclosed DEVIATION from ai-os-jc-toast's
    reference: that repo's C15-DEAD-REFERENCE check uses Severity.WARN (a
    targeted eval there found FAIL risked false positives across its own
    larger, more heterogeneous corpus). This function uses Severity.FAIL
    instead, per this task's own explicit test specification ("an artifact
    with a dead link -> FAIL"). See reference_scan.py's own docstring for
    the full rationale and the known false-positive class this repo hasn't
    yet observed but could hit later (at which point WARN + a soft-ref-
    equivalent convention would be the natural revision, not pre-built for
    a problem not yet seen here).
    """
    all_findings = scan_references(artifact)
    findings = [f for f in all_findings if f.check_id in C_R5_CHECK_IDS]

    verdict = roll_up_verdict(findings, applies=True)
    evidence = _format_evidence(verdict, findings)
    evidence = (
        f"{evidence} Source: native live markdown-link scan (single-source, "
        f"not mixed with a baseline lookup - this repo has no baseline-"
        f"findings.json/CI ratchet mechanism to route a corpus-level half "
        f"to; see reference_scan.py for the full single-vs-mixed-source "
        f"rationale)."
    )

    return DeterministicVerdict(
        criterion_id="C-R5",
        criterion_label="Wayfinding & Navigation",
        persona="eval-alumni-sam-rodriguez",
        domain="Accessibility & UX Architecture",
        verdict=verdict,
        evidence=evidence,
        check_ids=list(C_R5_CHECK_IDS),
        source=VerdictSource(
            mode="live-artifact-scan",
            detail=f"validators.reference_scan.scan_references({artifact.path})",
            computed_at=computed_at or _now_iso(),
        ),
        findings=[f.to_dict() for f in findings],
    )


# ---- C-N4 (T-13, FOURTH of the 4 remaining criteria - LAST this cycle) ---
#
# C-N4 Token Efficiency (Dr. Nakamura, AI Systems domain) is the plan's one
# genuinely NEW check - no existing check family here (PII regex, security
# regex, dead-link scan) wraps token counting, so this module owns the
# counting logic itself. See this module's own top docstring for the full
# judgment-call rationale (tokenizer availability re-check, budget source).

# Single check_id - C-N4 has exactly one check (character/token count vs.
# budget), same single-id shape as C-R5-CHECK_IDS above.
C_N4_CHECK_IDS = ["N4-TOKEN-BUDGET"]

# Re-confirmed directly for aios-eval (not assumed from the ai-os-jc-toast
# finding): `import tiktoken` raises ModuleNotFoundError in this repo's own
# Python environment too. 4 chars/token is the commonly cited approximation
# ratio for English-language text with common BPE-family tokenizers.
CHARS_PER_TOKEN = 4

# Reuses THIS repo's own already-documented "too long" figure -
# plugins/skills-toolkit/skills/skills-toolkit/references/agents/
# refactoring-patterns.md: "Agent exceeds ~10,000 tokens" / "under 8,000
# tokens with no clear redundancy" - not copied from ai-os-jc-toast's
# constant, though the two repos independently agree on the same number.
# A starting default the eval committee can revise, not a platform limit.
DEFAULT_TOKEN_BUDGET = 10_000


def _format_c_n4_evidence(
    verdict: str, char_count: int, token_estimate: int, budget_tokens: int
) -> str:
    """C-N4's own evidence formatter. Per this task's explicit honesty
    requirement, ALWAYS states the actual character count, the
    approximated token count, and the budget threshold - even on a clean
    PASS (unlike _format_evidence()'s bare 'PASS - no findings.'
    convention), because the whole point of this criterion is the count
    itself."""
    if verdict == "N/A":
        return "N/A - check does not apply to this artifact type."

    approximation_note = (
        f"~{token_estimate} tokens (approximated from {char_count} characters at "
        f"~{CHARS_PER_TOKEN} chars/token - no tokenizer library, e.g. tiktoken, is "
        f"installed in this environment, so this is a character-count proxy, not an "
        f"exact tokenizer count)"
    )
    budget_note = (
        f"budget is {budget_tokens} tokens (default starting threshold, reused from "
        f"this repo's own skills-toolkit/references/agents/refactoring-patterns.md "
        f"'agent exceeds 10,000 tokens' guidance - revisable by the eval committee, "
        f"not a hard platform limit)"
    )

    if verdict == "FAIL":
        over_by = token_estimate - budget_tokens
        return (
            f"FAIL (N4-TOKEN-BUDGET) - {approximation_note}, exceeding the budget by "
            f"~{over_by} tokens. {budget_note}."
        )
    return f"PASS (N4-TOKEN-BUDGET) - {approximation_note}, within budget. {budget_note}."


def compute_c_n4_verdict(
    artifact: Artifact,
    computed_at: Optional[str] = None,
    budget_tokens: int = DEFAULT_TOKEN_BUDGET,
) -> DeterministicVerdict:
    """C-N4 Token Efficiency (Dr. Nakamura, AI Systems domain) - a live,
    self-contained character/token count against a budget threshold. No
    existing check family to route to (unlike C-W1/C-W2/C-R5) - this is
    the plan's one genuinely NEW check.

    The counted "prompt file" is artifact.raw (frontmatter + body
    combined), not artifact.body alone - a deliberate difference from
    compute_c_w2_verdict's body-only PII scan target. The frontmatter
    (name, description, tools list) is also loaded into context every
    time this artifact is read as a prompt, so excluding it would
    understate the real token cost this criterion measures.

    Going over budget rolls up to a hard FAIL, not a WARN - this is exact
    arithmetic, not a fuzzy/false-positive-prone proxy like a regex match,
    so there is no reason to soften it the way C-W1's regex-based checks
    do.
    """
    prompt_text = artifact.raw
    char_count = len(prompt_text)
    token_estimate = math.ceil(char_count / CHARS_PER_TOKEN)

    if token_estimate > budget_tokens:
        findings = [
            Finding(
                check_id="N4-TOKEN-BUDGET",
                family="N4",
                severity=Severity.FAIL,
                artifact=str(artifact.path),
                message=(
                    f"~{token_estimate} tokens (from {char_count} chars, "
                    f"~{CHARS_PER_TOKEN} chars/token approximation) exceeds the "
                    f"{budget_tokens}-token budget by ~{token_estimate - budget_tokens} tokens"
                ),
            )
        ]
    else:
        findings = [
            Finding(
                check_id="N4-TOKEN-BUDGET",
                family="N4",
                severity=Severity.INFO,
                artifact=str(artifact.path),
                message=(
                    f"~{token_estimate} tokens (from {char_count} chars, "
                    f"~{CHARS_PER_TOKEN} chars/token approximation), "
                    f"~{budget_tokens - token_estimate} tokens under the "
                    f"{budget_tokens}-token budget"
                ),
            )
        ]

    verdict = roll_up_verdict(findings, applies=True)
    evidence = _format_c_n4_evidence(verdict, char_count, token_estimate, budget_tokens)

    return DeterministicVerdict(
        criterion_id="C-N4",
        criterion_label="Token Efficiency",
        persona="eval-alumni-dr-nakamura",
        domain="AI Systems",
        verdict=verdict,
        evidence=evidence,
        check_ids=list(C_N4_CHECK_IDS),
        source=VerdictSource(
            mode="live-artifact-scan",
            detail=(
                f"char/token count of artifact.raw (frontmatter + body) for "
                f"{artifact.path}, budget={budget_tokens} tokens"
            ),
            computed_at=computed_at or _now_iso(),
        ),
        findings=[f.to_dict() for f in findings],
    )


# ---- C-H1 (T-13, FIFTH and LAST of aios-eval's 5 criteria) --------------
#
# C-H1 Technical Correctness (Doc Hartwell, Technical Correctness domain) is
# the plan's one criterion needing LANGUAGE DETECTION + multi-toolchain
# dispatch, per criteria-classification.md's own framing: "'syntax
# accuracy' and 'type safety' are not proxied by a compiler/type-checker/
# linter - they are literally what those terms mean. Check: run the
# artifact's language toolchain; PASS if zero errors, FAIL with cited line
# otherwise. Scope note: N/A... for prose SKILL.md/agent .md artifacts,
# which is the majority case here - that's an applicability gap, not
# subjectivity."
#
# Unlike C-W1/C-R5 above, this criterion needs no infrastructure this repo
# lacks: ast.parse() is Python's own stdlib parser (already imported here,
# zero new dependency) and `bash -n` is bash's own built-in syntax-only
# parse mode (zero install, ships with bash itself) - both confirmed
# directly present in THIS repo's own environment before writing anything.
# `shellcheck` was considered and deliberately NOT used, same reasoning
# the ai-os-jc-toast reference already documented: a real, avoidable
# external-binary dependency for a pytest-covered function, with no
# guarantee of being present in every environment this suite runs in -
# `bash -n` needs no such guard.

# Both toolchains this criterion can dispatch to, listed together
# regardless of which one actually ran for a given artifact - matching
# every other criterion's own check_ids convention here (e.g.
# compute_c_w2_verdict always reports all 7 C6-PII-* ids even when only
# one fired for a given artifact).
C_H1_CHECK_IDS = ["H1-PY-SYNTAX", "H1-SH-SYNTAX"]

_H1_LANGUAGE_BY_SUFFIX = {".py": "python", ".sh": "bash"}

_BASH_BIN = shutil.which("bash") or "bash"


def _check_python_syntax(source: str, artifact_path: str) -> Finding:
    """The literal Python "compiler" for syntax purposes - ast.parse() is
    the standard library's own parser. A SyntaxError's own `lineno`/`msg`
    attributes give the cited line this criterion's own classification
    text requires ("FAIL with cited line")."""
    try:
        ast.parse(source, filename=artifact_path)
    except (SyntaxError, ValueError) as exc:
        line = getattr(exc, "lineno", None)
        line_text = f"line {line}" if line is not None else "unknown line"
        return Finding(
            check_id="H1-PY-SYNTAX",
            family="H1",
            severity=Severity.FAIL,
            artifact=artifact_path,
            message=f"{line_text}: {getattr(exc, 'msg', str(exc))}",
        )
    return Finding(
        check_id="H1-PY-SYNTAX",
        family="H1",
        severity=Severity.INFO,
        artifact=artifact_path,
        message="ast.parse: 0 syntax errors",
    )


def _check_bash_syntax(source: str, artifact_path: str) -> Finding:
    """`bash -n` over stdin - a syntax-only parse pass, no execution. If
    bash itself is somehow unavailable in a given environment, this
    degrades to UNTESTED rather than silently reporting a false PASS."""
    try:
        result = subprocess.run(
            [_BASH_BIN, "-n"],
            input=source,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return Finding(
            check_id="H1-SH-SYNTAX",
            family="H1",
            severity=Severity.UNTESTED,
            artifact=artifact_path,
            message=f"bash -n unavailable or failed to run: {exc}",
        )
    if result.returncode != 0:
        message = result.stderr.strip() or "bash -n reported a syntax error"
        return Finding(
            check_id="H1-SH-SYNTAX",
            family="H1",
            severity=Severity.FAIL,
            artifact=artifact_path,
            message=message,
        )
    return Finding(
        check_id="H1-SH-SYNTAX",
        family="H1",
        severity=Severity.INFO,
        artifact=artifact_path,
        message="bash -n: 0 syntax errors",
    )


def _format_c_h1_evidence(verdict: str, findings: list, language: str, tool_detail: str) -> str:
    """C-H1's own evidence formatter - deliberately not a call to the
    generic _format_evidence() above, which never names which tool ran.
    Since this criterion's entire mechanism IS language detection +
    per-language toolchain dispatch, always naming the language and tool
    is load-bearing here, mirroring why C-R5/C-W1 needed their own
    evidence suffixes above instead of the bare generic formatter."""
    fail_findings = [f for f in findings if f.severity == Severity.FAIL]
    if fail_findings:
        cited = "; ".join(f"{f.check_id}: {f.message}" for f in fail_findings)
        return f"FAIL - {tool_detail} ({language}) found a syntax error: {cited}."
    if findings:
        info = "; ".join(f.message for f in findings)
        return f"PASS - {tool_detail} ({language}): {info}."
    return f"PASS - {tool_detail} ({language}): 0 errors."


_H1_SCOPE_NOTE = (
    "N/A - {path} ({suffix}) is not a code artifact this criterion's "
    "toolchain check applies to (only .py/.sh are dispatched today). "
    "Scope note per criteria-classification.md: prose SKILL.md/agent .md "
    "artifacts (this plugin's actual majority case) are N/A by design - "
    "an applicability gap, not a subjective judgment call."
)


def compute_c_h1_verdict(
    artifact: Artifact, computed_at: Optional[str] = None
) -> DeterministicVerdict:
    """C-H1 Technical Correctness (Doc Hartwell, Technical Correctness
    domain) - detects the artifact's language by file extension and
    dispatches to that language's own toolchain: ast.parse() for .py,
    `bash -n` for .sh. Every other extension (including the .md prose
    artifacts that make up this plugin's actual majority case) resolves
    N/A, per criteria-classification.md's own explicit framing of that as
    an applicability gap, not subjectivity.

    Unlike C-W1/C-R5 above, this is a faithful full port of the
    ai-os-jc-toast reference's shape - no scope reduction was needed,
    since both toolchains (ast.parse, bash -n) are zero-install and
    already confirmed present in this repo's own environment.
    """
    suffix = artifact.path.suffix.lower()
    artifact_path = str(artifact.path)
    language = _H1_LANGUAGE_BY_SUFFIX.get(suffix)

    if language is None:
        verdict = roll_up_verdict([], applies=False)
        evidence = _H1_SCOPE_NOTE.format(path=artifact_path, suffix=suffix or "(no extension)")
        return DeterministicVerdict(
            criterion_id="C-H1",
            criterion_label="Technical Correctness",
            persona="eval-alumni-doc-hartwell",
            domain="Technical Correctness",
            verdict=verdict,
            evidence=evidence,
            check_ids=list(C_H1_CHECK_IDS),
            source=VerdictSource(
                mode="live-artifact-scan",
                detail=f"not applicable - {suffix or '(no extension)'} is not a dispatched code extension",
                computed_at=computed_at or _now_iso(),
            ),
            findings=[],
        )

    if suffix == ".py":
        finding = _check_python_syntax(artifact.raw, artifact_path)
        tool_detail = f"ast.parse({artifact_path})"
    else:  # .sh
        finding = _check_bash_syntax(artifact.raw, artifact_path)
        tool_detail = f"bash -n {artifact_path}"

    findings = [finding]
    verdict = roll_up_verdict(findings, applies=True)
    evidence = _format_c_h1_evidence(verdict, findings, language, tool_detail)

    return DeterministicVerdict(
        criterion_id="C-H1",
        criterion_label="Technical Correctness",
        persona="eval-alumni-doc-hartwell",
        domain="Technical Correctness",
        verdict=verdict,
        evidence=evidence,
        check_ids=list(C_H1_CHECK_IDS),
        source=VerdictSource(
            mode="live-artifact-scan",
            detail=tool_detail,
            computed_at=computed_at or _now_iso(),
        ),
        findings=[f.to_dict() for f in findings],
    )
