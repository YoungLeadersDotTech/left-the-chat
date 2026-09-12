"""Native, deliberately lightweight dead-markdown-link scanner for aios-eval's
C-R5 "Wayfinding & Navigation" criterion (T-13, eval-committee-deterministic-
validators plan, Phase 4).

Confirmed before writing this module (not assumed): aios-eval has NO existing
dead-link/orphan-reference infrastructure of any kind. A repo-wide grep for
"dead", "orphan", "reference" across plugins/aios-eval/ turned up exactly one
hit - a CHANGELOG.md prose mention of an external validate-marketplace sweep
having fixed "C16 orphan-reference links" in this plugin's own files at some
point in the past - not a native check module living in this repo. Also
confirmed: no baseline-findings.json/CI ratchet file exists anywhere in this
repo (repo-wide grep for "baseline-findings"/"generated_at": zero hits).

Unlike ai-os-jc-toast's compute_c_r5_verdict (T-09,
plugins/toast-plugin-validator/validators/deterministic_verdict.py), which is
genuinely MIXED-source (C15-DEAD-REFERENCE live-scan + C16-ORPHAN-REFERENCE-
FILE/C17-CROSS-PLUGIN-FILE-REFERENCE baseline-lookup, because that repo
already has a committed baseline-findings.json CI ratchet mechanism to route
the corpus-level half to), this native aios-eval version is SINGLE-source:
only the live, per-artifact dead-markdown-link check. There is no C16/C17
baseline half here because there is no baseline mechanism in this repo to
look up against - per this task's own explicit instruction, one is NOT
invented from scratch just to mirror ai-os-jc-toast's shape. If aios-eval
ever gets its own CI ratchet mechanism, a baseline-lookup half could be added
later the same way compute_c_w1_verdict's own docstring already flags a
future baseline-lookup upgrade path for that criterion.

Severity choice - a deliberate, disclosed DEVIATION from the ai-os-jc-toast
reference: that repo's C15-DEAD-REFERENCE check uses Severity.WARN, not
FAIL, specifically because a targeted eval before lock-in there flagged FAIL
as risking false positives across that repo's much larger, more
heterogeneous corpus (prose/code-fence path-shaped text, its own
"[soft-ref]" optional-reference convention). This module uses Severity.FAIL
instead, per this task's own explicit test specification ("an artifact with
a dead link -> FAIL"). This is a real, disclosed choice, not an oversight:
if the same false-positive class ai-os-jc-toast's eval run found ever turns
up in this repo's own artifacts, downgrading to WARN (and adding a
soft-ref-equivalent convention) is the natural next revision - not built
pre-emptively here for a problem not yet observed in this repo.

Scope decision (documented, not asked): a small, curated markdown-link
scanner - real `[text](target)` syntax only, checked directly against
on-disk file existence. Deliberately NOT ported from ai-os-jc-toast's fuller
discover_references() for this first native version, matching this task's
own "much simpler...no baseline/corpus-level complexity needed" framing:
  - fenced-code-block / inline-code-span stripping before link scanning
    (ai-os-jc-toast's own T-B34 KTLO fix, added after a real false positive
    was observed there on illustrative example links quoted as code)
  - the "[soft-ref]" optional-reference exemption marker
  - non-markdown-file / orphan-reference / cross-plugin-reference checks
    (ai-os-jc-toast's C16/C17 - corpus-level, no counterpart here)
Known, disclosed gap this omission could cause: an artifact that quotes a
link (e.g. `[example](./sample.md)`) purely as documentation/example prose
inside a code fence would currently be scanned as a real link and flagged if
`./sample.md` doesn't exist - the same false-positive class ai-os-jc-toast's
T-B34 fix addressed there. Flagged here, not fixed, since it has not been
observed as a real problem in this repo's own artifacts yet - the same
"disclose, don't pre-build for an unobserved problem" posture
security_scan.py's own docstring already takes for its own known gaps.

Resolution order (mirrors ai-os-jc-toast's own discover_references()):
relative link targets resolve against the artifact's own directory first,
falling back to the artifact's plugin root (first path segment under this
repo's own `plugins/` directory) if that fails.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from validators.artifact import Artifact
from validators.findings import Finding, Severity

# Real markdown link syntax only - [text](target) - never bare relative-path
# mentions in prose. An optional in-file anchor (#section) is stripped from
# the target separately, below.
_MD_LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)\s]+)\)")

# Skips a target that starts with a URL scheme (http://, https://, mailto:,
# etc.) - those are never local file references. Same pattern shape as
# ai-os-jc-toast's own _URL_SCHEME_RE.
_URL_SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.\-]*:(?://|[^/])")

C15_DEAD_REFERENCE_CHECK_ID = "C15-DEAD-REFERENCE"


def _find_plugins_dir(path: Path) -> Optional[Path]:
    for parent in path.parents:
        if parent.name == "plugins":
            return parent
    return None


def _plugin_root_for(path: Path) -> Path:
    """First path segment under this repo's own plugins/ directory - falls
    back to the artifact's own containing directory when no `plugins/`
    ancestor is found (e.g. a fixture path with no realistic repo layout),
    mirroring the own_dir fallback ai-os-jc-toast's own plugin_root_for()/
    discover_references() pair already uses."""
    plugins_dir = _find_plugins_dir(path)
    if plugins_dir is None:
        return path.parent
    rel = path.relative_to(plugins_dir)
    return plugins_dir / rel.parts[0]


def scan_references(artifact: Artifact) -> list:
    """Scan an artifact's full text for real markdown links whose target
    does not resolve to an existing file on disk. Returns a flat list of
    Finding objects (may be empty). URL-scheme targets (http://, mailto:,
    etc.) and in-page anchors (#section) are skipped - only local file
    targets are checked."""
    own_dir = artifact.path.parent
    plugin_root = _plugin_root_for(artifact.path)
    artifact_path = str(artifact.path)

    findings: list = []
    for m in _MD_LINK_RE.finditer(artifact.raw):
        target = m.group(2)
        if _URL_SCHEME_RE.match(target) or target.startswith("#"):
            continue
        target_path = target.split("#", 1)[0]  # strip in-file anchor
        if not target_path:
            continue

        candidate = (own_dir / target_path).resolve()
        if not candidate.is_file():
            candidate = (plugin_root / target_path).resolve()
        if candidate.is_file():
            continue

        findings.append(Finding(
            check_id=C15_DEAD_REFERENCE_CHECK_ID, family="C15",
            severity=Severity.FAIL, artifact=artifact_path,
            message=(
                f"Reference '{target_path}' does not resolve to an existing "
                f"file (checked relative to {own_dir} and plugin root "
                f"{plugin_root})."
            ),
        ))
    return findings
