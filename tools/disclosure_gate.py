#!/usr/bin/env python3
"""Pre-publish disclosure gate.

Flipping a repository public is irreversible, and a term that reaches a public
repo reaches its history too. This scans a tree for internal terms before that
happens and answers one question: is it safe to publish this.

The blocklist has two tiers and the distinction matters. Blocking terms are
someone else's to disclose. Owned terms are the author's own projects, safe to
publish, and are reported as INFO so a public mention is always surfaced rather
than passing silently - visibility, not prevention. An owned term never changes
the verdict.

The blocklist path is supplied by --blocklist or $DISCLOSURE_BLOCKLIST and is
deliberately not hardcoded: this file is itself published, and a hardcoded home
path would disclose the directory layout it exists to protect.

Usage:
    python3 -m tools.disclosure_gate <path> [--mode public|work] [--blocklist PATH]

Exit codes:
    0  clean, or only INFO findings
    1  at least one BLOCK finding
    2  could not run (blocklist missing, target missing)
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path


class EmptyScanError(RuntimeError):
    """Raised when the gate would report a verdict without having checked anything.

    Exists because the failure that matters here is a false PASS, and the two
    cheapest routes to one are a blocklist that parses to no rules and a scan
    that reaches no files. Both are indistinguishable from "clean" in the output
    unless they are made loud.
    """

#: A blocklist entry. Two shapes occur in the real file and both must parse:
#:   - `term` - replacement - [category]
#:   - Any absolute path starting with `<prefix>` - BLOCK or generalise - [PII path]
#: The second shape carries prose before the term and a second backtick span after
#: it. Requiring a backtick immediately after "- " silently dropped every entry
#: under "## Credentials and paths" - six of roughly forty rules, including the
#: absolute-home-path rule that was live-leaking. The term is the FIRST backtick
#: span on the line; the category bracket at the end marks the line as an entry.
#:
#: Note: the examples above are written with placeholders rather than the real
#: terms on purpose. This file is scanned by the gate it implements, and quoting
#: a blocked term verbatim in a comment is indistinguishable from leaking it.
_ENTRY = re.compile(r"^-\s+(?:[^`]*?)`([^`]+)`\s*(.*?)\s*-\s*\[([^\]]*)\]\s*$")
_HEADING = re.compile(r"^##\s+(.*?)\s*$")

#: Secret classes, matched as real regex and compiled here rather than read from
#: the blocklist. Two reasons. Blocklist terms are matched literally (see
#: _scan_text), so a pattern expressed there is searched character-for-character
#: and can never fire. And a floor that lives in the blocklist can be removed by
#: editing a file in another repo - this one cannot be switched off at all.
#:
#: The prefixes are concatenated rather than written inline. The blocklist also
#: lists these classes as literal terms, so a contiguous copy of one here is a
#: literal match against this very file - the gate would block its own source.
#: Splitting the string leaves the compiled pattern identical and removes the
#: false match. Same reasoning as the placeholder comment above _ENTRY.
_SECRET_PATTERNS: tuple[tuple[re.Pattern[str], str, str], ...] = (
    (re.compile("AKIA" + r"[0-9A-Z]{16}"), "AWS access key id", "remove and rotate the key"),
    (re.compile("ASIA" + r"[0-9A-Z]{16}"), "AWS temporary key id", "remove and rotate the key"),
    (re.compile("ghp" + r"_[A-Za-z0-9]{36}"), "GitHub personal access token", "remove and revoke"),
    (re.compile(r"github_pat_[A-Za-z0-9_]{22,}"), "GitHub fine-grained PAT", "remove and revoke"),
    (re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"), "Slack token", "remove and revoke"),
    (re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}"), "Anthropic API key", "remove and rotate"),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "private key", "remove from the repo"),
    (re.compile("sk-proj" + r"-[A-Za-z0-9_-]{20,}"), "OpenAI project key", "remove and rotate"),
    (re.compile("AIza" + r"[A-Za-z0-9_-]{35}"), "Google API key", "remove and rotate"),
)

#: Files that are never worth scanning - binary, generated, or vendored.
_SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build"}
_SKIP_SUFFIXES = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".pdf", ".zip", ".gz",
    ".woff", ".woff2", ".ttf", ".mp4", ".mov", ".wasm", ".pyc",
}

#: Labels the secret floor attaches to its findings. Lets a credential finding be
#: told apart from an ordinary blocklist term at verdict time, so --mode work can
#: waive internal vocabulary without also waiving keys.
_SECRET_LABELS = frozenset(label for _pattern, label, _fix in _SECRET_PATTERNS)


@dataclass(frozen=True)
class Finding:
    severity: str  # "BLOCK" or "INFO"
    path: Path
    line: int
    term: str
    suggestion: str

    def render(self, root: Path | None = None) -> str:
        shown = self.path
        if root is not None:
            try:
                shown = self.path.relative_to(root)
            except ValueError:
                pass
        return f"{self.severity:<5}  {shown}:{self.line}  {self.term}  - {self.suggestion}"


def load_blocklist(path: Path) -> tuple[dict[str, str], dict[str, str]]:
    """Parse the blocklist into (blocking, owned) term -> suggestion maps.

    Everything under a heading containing "owned terms" is the INFO tier; every
    other section blocks. Matching on the heading rather than a fixed position
    means adding a section above it does not silently reclassify the owned terms.
    """
    if not path.is_file():
        raise FileNotFoundError(f"blocklist not found: {path}")

    blocking: dict[str, str] = {}
    owned: dict[str, str] = {}
    target = blocking
    in_section = False

    for raw in path.read_text(encoding="utf-8").splitlines():
        heading = _HEADING.match(raw)
        if heading:
            in_section = True
            target = owned if "owned terms" in heading.group(1).lower() else blocking
            continue
        if not in_section:
            # The preamble documents the entry format with a `pattern` placeholder
            # that matches the entry regex exactly. Only lines under a real section
            # heading are terms; everything above the first heading is prose.
            continue
        entry = _ENTRY.match(raw)
        if entry:
            term, suggestion, _category = entry.groups()
            # The prose shape leaves the separating "- " on the front of the
            # suggestion; the plain shape does not. Normalise so both render alike.
            target[term] = suggestion.lstrip("- ").strip()

    return blocking, owned


def _load_ignore_file(root: Path) -> list[str]:
    """Read `.disclosureignore` if present - one glob per line, # for comments."""
    ignore = root / ".disclosureignore"
    if not ignore.is_file():
        return []
    return [
        line.strip()
        for line in ignore.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def _matches_any(relative: Path, patterns: list[str]) -> bool:
    """Glob match against a path relative to the scan root.

    `Path.full_match` is 3.13+ and this package declares `requires-python >=3.11`,
    where it raises AttributeError on every non-matching file. `fnmatch` on the
    posix string covers the same cases (`tests/fixtures/*`, `*.md`) on every
    supported version.
    """
    text = relative.as_posix()
    return any(fnmatch(text, pattern) or relative.match(pattern) for pattern in patterns)


def _find_ignore_root(target: Path) -> Path | None:
    """Walk up from a file to the directory holding its `.disclosureignore`.

    Stops at a `.git` directory (the repo boundary) or the filesystem root, so a
    stray ignore file somewhere above the repo cannot silently widen the blind spot.
    """
    current = target.resolve().parent
    while True:
        if (current / ".disclosureignore").is_file():
            return current
        if (current / ".git").exists() or current.parent == current:
            return None
        current = current.parent


def _iter_files(
    target: Path,
    exclude: list[str] | None = None,
    suppressed: list[Path] | None = None,
):
    if target.is_file():
        yield target
        return
    patterns = list(exclude or [])
    for path in sorted(target.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(target)
        # Relative to the scan root, not absolute. Testing absolute parts meant a
        # scan rooted anywhere beneath a directory named build/ or dist/ skipped
        # every file in the tree and still reported PASS.
        if any(part in _SKIP_DIRS for part in relative.parts):
            continue
        if path.suffix.lower() in _SKIP_SUFFIXES:
            continue
        if _matches_any(relative, patterns):
            if suppressed is not None:
                suppressed.append(relative)
            continue
        yield path


#: A bare short all-caps acronym is exactly the shape that collides with
#: base64 in an integrity hash - digits and mixed-case letters on both sides
#: make a substring match near-arbitrary. A term with any other shape (a
#: domain, a phrase, a path fragment) still needs substring matching, since
#: that is how it actually leaks - inside a comment or a path, not on a line
#: by itself. So only this shape gets word boundaries. (Examples deliberately
#: omitted per the placeholder convention above _ENTRY - this file is scanned
#: by the gate it implements.)
_BARE_ACRONYM = re.compile(r"^[A-Z0-9]{2,6}$")


def _term_pattern(term: str) -> re.Pattern[str]:
    escaped = re.escape(term)
    if _BARE_ACRONYM.match(term):
        escaped = rf"\b{escaped}\b"
    return re.compile(escaped, re.IGNORECASE)


def _scan_text(text: str, path: Path, blocking, owned) -> list[Finding]:
    findings: list[Finding] = []
    lines = text.splitlines()
    for tier, severity in ((blocking, "BLOCK"), (owned, "INFO")):
        for term, suggestion in tier.items():
            # Blocklist terms are literals. Case-insensitive and
            # position-independent: the terms that actually leak are the ones
            # sitting inside a comment or a path, not the ones on a line by
            # themselves. Anything that needs to be a real pattern belongs in
            # _SECRET_PATTERNS, where it is compiled as regex and cannot be
            # removed by editing the blocklist. Bare acronyms are the one
            # exception - see _term_pattern.
            pattern = _term_pattern(term)
            for lineno, line in enumerate(lines, start=1):
                if pattern.search(line):
                    findings.append(Finding(severity, path, lineno, term, suggestion))
    for compiled, label, suggestion in _SECRET_PATTERNS:
        for lineno, line in enumerate(lines, start=1):
            if compiled.search(line):
                findings.append(Finding("BLOCK", path, lineno, label, suggestion))
    return findings


@dataclass(frozen=True)
class ScanResult:
    """Findings plus the evidence that any work was done to produce them.

    "Found nothing" and "looked at nothing" printed the same verdict before this
    existed, which is how the gate came to report Safe to publish over a tree
    containing a term its own blocklist banned.
    """

    findings: list[Finding]
    rules_loaded: int
    files_scanned: int
    #: Files an exclude glob or .disclosureignore kept out of the scan. Reported,
    #: never silent - an over-broad ignore line is indistinguishable from a clean
    #: repo otherwise, and it is the cheapest way to blind the gate by accident.
    suppressed: list[Path]


def scan_tree(
    target: Path, blocklist_path: Path, exclude: list[str] | None = None
) -> ScanResult:
    """Scan a file or directory. Raises EmptyScanError if nothing was checked."""
    blocking, owned = load_blocklist(blocklist_path)
    rules_loaded = len(blocking) + len(owned)
    if rules_loaded == 0:
        raise EmptyScanError(
            f"blocklist parsed to 0 terms: {blocklist_path}. The format has probably "
            "drifted - refusing to report a verdict against an empty rule set."
        )

    patterns = list(exclude or [])
    findings: list[Finding] = []
    files_scanned = 0
    suppressed: list[Path] = []

    if target.is_dir():
        patterns += _load_ignore_file(target)
        candidates = _iter_files(target, patterns, suppressed)
    else:
        # A single named file still has to honour the repo's .disclosureignore.
        # It did not, which meant the pre-commit hook - which scans one staged
        # file at a time by explicit path - blocked on the very fixtures the
        # ignore file exists to exempt, leaving --no-verify as the only way
        # through. A gate that has to be bypassed routinely stops being a gate.
        ignore_root = _find_ignore_root(target)
        if ignore_root is not None:
            relative = target.resolve().relative_to(ignore_root)
            if _matches_any(relative, _load_ignore_file(ignore_root)):
                suppressed.append(relative)
                candidates: list[Path] = []
            else:
                candidates = [target]
        else:
            candidates = [target]

    for path in candidates:
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue  # binary or unreadable - nothing to disclose in text terms
        files_scanned += 1
        findings.extend(_scan_text(text, path, blocking, owned))

    # A directory scan that reached zero files is ALWAYS an error, however it got
    # there. An earlier version exempted the case where everything had been
    # suppressed, on the reasoning that a deliberate exclusion is not a broken
    # run. That was wrong: a single over-broad ignore line (`*`) then produced
    # "38 rule(s) applied to 0 file(s). PASS" over a tree containing a real leak.
    # Suppression explains an empty scan; it does not make one safe.
    #
    # A single explicitly-named file that is exempt is the one legitimate no-op -
    # the pre-commit hook walks the staged files one at a time and some of them
    # are deliberately exempt fixtures. That case is handled above, where
    # `candidates` is empty for a file target, and is distinguished by the target
    # being a file rather than by anything about the suppression itself.
    if files_scanned == 0 and target.is_dir():
        raise EmptyScanError(
            f"scanned 0 files under {target} - every candidate was excluded, skipped "
            "or unreadable. Refusing to report a verdict on an empty scan."
        )

    findings.sort(key=lambda f: (f.severity != "BLOCK", str(f.path), f.line))
    return ScanResult(findings, rules_loaded, files_scanned, sorted(suppressed))


def scan_path(
    target: Path, blocklist_path: Path, exclude: list[str] | None = None
) -> list[Finding]:
    """Findings only, most severe first. Thin wrapper over `scan_tree`."""
    return scan_tree(target, blocklist_path, exclude).findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("target", type=Path, help="file or directory to scan")
    parser.add_argument(
        "--mode",
        choices=("public", "work"),
        default="public",
        help="public blocks internal terms; work allows them (the blocklist's own rule)",
    )
    parser.add_argument(
        "--blocklist",
        type=Path,
        default=os.environ.get("DISCLOSURE_BLOCKLIST"),
        help="path to toast-blocklist.md (or set $DISCLOSURE_BLOCKLIST)",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        metavar="GLOB",
        help="skip paths matching this glob; repeatable. A .disclosureignore file "
        "in the scanned directory is read as well.",
    )
    args = parser.parse_args(argv)

    if args.blocklist is None:
        print("error: no blocklist given - pass --blocklist or set $DISCLOSURE_BLOCKLIST")
        return 2
    if not args.target.exists():
        print(f"error: target not found: {args.target}")
        return 2

    try:
        result = scan_tree(args.target, Path(args.blocklist), exclude=args.exclude)
    except (FileNotFoundError, EmptyScanError) as exc:
        print(f"error: {exc}")
        return 2

    root = args.target if args.target.is_dir() else args.target.parent
    for finding in result.findings:
        print(finding.render(root))

    if result.suppressed:
        print(f"\nSUPPRESSED - {len(result.suppressed)} file(s) excluded from this scan:")
        for relative in result.suppressed:
            print(f"  {relative}")

    blocked = [f for f in result.findings if f.severity == "BLOCK"]
    info = [f for f in result.findings if f.severity == "INFO"]
    # Every verdict carries its own evidence of work. A PASS that cannot say how
    # many rules it applied and how many files it read is not a PASS worth having.
    evidence = f"{result.rules_loaded} rule(s) applied to {result.files_scanned} file(s)"

    if args.mode == "work":
        # Internal terms are allowed in work mode - that is the blocklist's own
        # rule. Credentials are NOT. The secret floor is documented as something
        # that cannot be switched off, and this early return used to switch it
        # off: secret findings carry severity BLOCK like any other, so a
        # hardcoded private key printed PASS under --mode work. A flag that
        # disables the credential check is a flag that publishes a key.
        secrets = [f for f in blocked if f.term in _SECRET_LABELS]
        if secrets:
            print(
                f"\n{len(secrets)} credential finding(s) - not waivable by --mode work. "
                f"{evidence}. FAIL"
            )
            return 1
        print(
            f"\nmode=work - {len(blocked)} internal term(s) allowed, {len(info)} owned. "
            f"{evidence}. PASS"
        )
        return 0

    if blocked:
        print(f"\n{len(blocked)} blocking finding(s). {evidence}. Do not publish. FAIL")
        return 1

    print(f"\nNo blocking findings, {len(info)} owned term(s) noted. {evidence}. PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
