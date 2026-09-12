"""Minimal Artifact data shape for aios-eval's deterministic validators.

Native, deliberately minimal port of toast-plugin-validator's
validators/artifact.py (ai-os-jc-toast) - that source file is 345 lines
covering frontmatter parsing, ArtifactType classification, and reference
extraction none of which T-12a/b's scope needs yet (only `path` + `raw`,
the full file text a PII scan runs over). Extend this shape if/when a later
task (T-13+) needs frontmatter-aware or artifact-type-gated checks.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Artifact:
    path: Path
    raw: str  # full file text (frontmatter + body combined) - the same
    # scan target compute_c_w2_verdict's ai-os-jc-toast counterpart uses.


def load_artifact(path: str | Path) -> Artifact:
    """Read a real file off disk into an Artifact. Not used by the test
    suite (which constructs Artifact directly, matching T-08a's convention)
    - provided for the eventual Step 4.0-equivalent CLI wiring (T-13+)."""
    p = Path(path)
    return Artifact(path=p, raw=p.read_text())
