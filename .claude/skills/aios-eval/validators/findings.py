"""Finding/Severity data shape for aios-eval's deterministic validators.

Native, minimal port of toast-plugin-validator's validators/findings.py
(ai-os-jc-toast) shape - not a cross-repo import, per
phase2-mechanism-design.md's Decision 1 ("one shared contract, two native
implementations"; aios-eval is a separate repo/org and cannot import across
repos). Only the FAIL/WARN/INFO/UNTESTED severities are ported (aios-eval
has no --strict CI gate or ADVISORY-tier opt-in findings today, so that
fifth severity from the source repo is not needed here yet).
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class Severity(str, Enum):
    FAIL = "FAIL"
    WARN = "WARN"
    INFO = "INFO"
    UNTESTED = "UNTESTED"


@dataclass(frozen=True)
class Finding:
    check_id: str
    family: str
    severity: Severity
    artifact: str
    message: str
    line: Optional[int] = None

    def to_dict(self) -> dict:
        severity = self.severity.value if isinstance(self.severity, Severity) else self.severity
        return {
            "check_id": self.check_id,
            "family": self.family,
            "severity": severity,
            "artifact": self.artifact,
            "message": self.message,
            "line": self.line,
        }
