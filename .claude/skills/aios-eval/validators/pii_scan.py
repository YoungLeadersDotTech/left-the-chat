"""C6-equivalent PII detection engine, natively ported from ai-os-jc-toast's
`toast-plugin-validator/validators/checks/c06_pii.py` (T-10's own port of the
pii-detection-patterns reference skill).

Not a cross-repo import (aios-eval is a separate repo/org - see
phase2-mechanism-design.md Decision 1): the regex categories, severities, and
exemption logic are copied as a native module operating over this repo's own
minimal Artifact/Finding shapes (validators/artifact.py, validators/findings.py).

Scope (T-12b): only the six regex-pattern categories plus the IP-address
check that ai-os-jc-toast's C_W2_CHECK_IDS names are ported - the same set,
no more, no less. No CheckRegistry/@check decorator system exists in this
repo yet (unlike toast-plugin-validator's registry.py) - aios-eval only has
this one check family so far, so `scan_pii()` is a single plain function
rather than a registered-check abstraction. If T-13 adds more check families
here, revisit whether a shared registry is worth introducing then.
"""
from __future__ import annotations

import ipaddress
import json
import re
from pathlib import Path

from validators.artifact import Artifact
from validators.findings import Finding, Severity

_DATA_PATH = Path(__file__).resolve().parent / "data" / "pii-patterns.json"
_DATA = json.loads(_DATA_PATH.read_text())

_FENCE_RE = re.compile(r"^`{3,}.*?^`{3,}\s*$", re.MULTILINE | re.DOTALL)
_SEVERITY_MAP = {"FAIL": Severity.FAIL, "WARN": Severity.WARN, "INFO": Severity.INFO}


def _strip_fences(text: str) -> str:
    """A fenced code block is a common source of placeholder emails/cards/
    addresses in illustrative example payloads - strip it before scanning,
    matching the source repo's own _strip_fences convention."""
    return _FENCE_RE.sub("", text)


def _is_safe_email(match_text: str, safe_domains: list) -> bool:
    domain = match_text.rsplit("@", 1)[-1].lower()
    return any(domain == d or domain.endswith("." + d) for d in safe_domains)


def _is_safe_test_phone(match_text: str) -> bool:
    """US reserved test range 555-0100 through 555-0199 (FCC/NANPA)."""
    digits = re.sub(r"\D", "", match_text)
    last7 = digits[-7:]
    return len(last7) == 7 and last7[:5] == "55501"


def _is_safe_test_card(match_text: str, safe_numbers: list) -> bool:
    digits = re.sub(r"\D", "", match_text)
    return digits in (safe_numbers or [])


def _scan_pattern_category(entry: dict, text: str, artifact_path: str) -> list:
    check_id = entry["id"]
    label = entry["label"]
    severity = _SEVERITY_MAP[entry["severity"]]
    pattern = re.compile(entry["regex"])

    matches = [m.group(0) for m in pattern.finditer(text)]
    if not matches:
        return []

    if check_id == "C6-PII-EMAIL":
        matches = [m for m in matches if not _is_safe_email(m, entry.get("safe_email_domains"))]
    elif check_id == "C6-PII-PHONE":
        matches = [m for m in matches if not _is_safe_test_phone(m)]
    elif check_id == "C6-PII-CREDIT-CARD":
        matches = [m for m in matches if not _is_safe_test_card(m, entry.get("safe_credit_card_test_numbers"))]

    if not matches:
        return []
    return [Finding(
        check_id=check_id, family="C6", severity=severity, artifact=artifact_path,
        message=(
            f"possible {label} detected ({len(matches)} match(es)) - "
            f"replace with a placeholder"
        ),
    )]


_PRIVATE_NETS = [
    ipaddress.ip_network(n)
    for n in (
        "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "127.0.0.0/8",
        # RFC 5737 documentation ranges (TEST-NET-1/2/3) - standard
        # placeholder addresses in illustrative example payloads.
        "192.0.2.0/24", "198.51.100.0/24", "203.0.113.0/24",
    )
]
_IP_RE = re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b")


def _scan_public_ip(text: str, artifact_path: str) -> list:
    public_ips = []
    for m in _IP_RE.findall(text):
        try:
            addr = ipaddress.ip_address(m)
        except ValueError:
            continue
        if not any(addr in net for net in _PRIVATE_NETS):
            public_ips.append(m)
    if not public_ips:
        return []
    return [Finding(
        check_id="C6-PII-IP", family="C6", severity=Severity.INFO,
        artifact=artifact_path,
        message=(
            f"possible public IP address(es) detected: {sorted(set(public_ips))} - "
            f"review for sensitivity (private/localhost ranges are exempt)"
        ),
    )]


def scan_pii(artifact: Artifact) -> list:
    """Scan an artifact's full text for all C6-PII-* categories. Returns a
    flat list of Finding objects (may be empty)."""
    text = _strip_fences(artifact.raw)
    artifact_path = str(artifact.path)
    findings: list = []
    for entry in _DATA["categories"]:
        findings.extend(_scan_pattern_category(entry, text, artifact_path))
    findings.extend(_scan_public_ip(text, artifact_path))
    return findings
