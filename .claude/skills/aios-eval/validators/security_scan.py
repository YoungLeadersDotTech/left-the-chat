"""Native, deliberately lightweight security anti-pattern scanner for
aios-eval's C-W1 "Security Vulnerabilities" criterion (T-13,
eval-committee-deterministic-validators plan, Phase 4).

Unlike C-W2's pii_scan.py (which IS a faithful native port of an existing
ai-os-jc-toast check, c06_pii.py), this module has no upstream counterpart
to port: ai-os-jc-toast's own C-W1 (compute_c_w1_verdict, T-09) routes to a
baseline-lookup against a corpus-level bandit/semgrep CI scan
(baseline-findings.json) - infrastructure this repo does not have. Confirmed
directly (not assumed) via a repo-wide grep for "bandit", "semgrep", and
"SEC-" across every .py/.md/.json file before writing this module: zero
hits. Building a full bandit/semgrep-equivalent SAST pipeline (a real
scanner dependency, a corpus-level CI job, a baseline ratchet file) from
scratch for one criterion in one autonomous cron cycle would be
disproportionate scope for this task.

Scope decision (documented, not asked): this is architecturally closer to
C-W2's compute_c_w2_verdict (a live-artifact-scan over artifact.raw) than
to C-W1's own ai-os-jc-toast shape (a baseline-lookup). A small, curated set
of regex anti-patterns is checked directly against the artifact text:

  - SEC-001: hardcoded secrets/credentials (API keys, passwords, tokens,
    AWS access key IDs, PEM private key headers)
  - SEC-003: dangerous dynamic code execution (eval/exec) and shell
    injection (os.system, os.popen, subprocess.*(..., shell=True))

check_id numbers are chosen to align with ai-os-jc-toast's own
bandit_security.py catalogue naming for the SAME anti-pattern families (see
validators/data/security-patterns.json's own "_meta" block for the mapping
rationale) - readability only, not a claim of equivalent detection power.

Known, disclosed scope reduction vs. ai-os-jc-toast's bandit/semgrep-backed
version: this is a lightweight regex-based check, not a full SAST
equivalent. No SQL injection, weak-crypto, path-traversal, deserialization,
SSRF, or XSS coverage (those need AST/taint-flow analysis to check with any
precision - see security-patterns.json's "_meta.known_gaps" for the full
list). It also cannot distinguish real dangerous code from prose that
merely discusses these patterns (e.g. "avoid using eval()" would
false-positive) - an inherent limitation of text-pattern matching without
AST/context awareness.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from validators.artifact import Artifact
from validators.findings import Finding, Severity

_DATA_PATH = Path(__file__).resolve().parent / "data" / "security-patterns.json"
_DATA = json.loads(_DATA_PATH.read_text())

_FENCE_RE = re.compile(r"^`{3,}.*?^`{3,}\s*$", re.MULTILINE | re.DOTALL)
_SEVERITY_MAP = {"FAIL": Severity.FAIL, "WARN": Severity.WARN, "INFO": Severity.INFO}


def _is_safe_placeholder(matched_text: str, safe_substrings: list) -> bool:
    """Case-insensitive substring check against a curated placeholder-marker
    list (e.g. 'YOUR_API_KEY_HERE', 'changeme') - exempts the common
    documentation pattern of showing a config key with an obvious
    instructional stand-in value, rather than a real secret."""
    lowered = matched_text.lower()
    return any(marker in lowered for marker in (safe_substrings or []))


def _scan_pattern_category(entry: dict, text: str, artifact_path: str) -> list:
    check_id = entry["id"]
    label = entry["label"]
    severity = _SEVERITY_MAP[entry["severity"]]
    pattern = re.compile(entry["regex"])

    safe_substrings = entry.get("safe_value_substrings")
    matches = [
        m.group(0) for m in pattern.finditer(text)
        if not (safe_substrings and _is_safe_placeholder(m.group(0), safe_substrings))
    ]
    if not matches:
        return []

    return [Finding(
        check_id=check_id, family="SEC", severity=severity, artifact=artifact_path,
        message=(
            f"possible {label} detected ({len(matches)} match(es)) - "
            f"review and remove before committing"
        ),
    )]


def scan_security(artifact: Artifact) -> list:
    """Scan an artifact's full text for all SEC-* security anti-pattern
    categories currently defined (SEC-001, SEC-003). Fenced code blocks are
    NOT stripped (unlike pii_scan.py's _strip_fences) - security anti-
    patterns most often live inside the fenced code examples this validator
    package's artifacts contain, so stripping them would blind the check to
    its primary target. Returns a flat list of Finding objects (may be
    empty)."""
    text = artifact.raw
    artifact_path = str(artifact.path)
    findings: list = []
    for entry in _DATA["categories"]:
        findings.extend(_scan_pattern_category(entry, text, artifact_path))
    return findings
