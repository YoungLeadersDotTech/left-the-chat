"""Tests for the pre-publish disclosure gate.

The gate exists because flipping a repo public is irreversible. These tests are the
only thing standing between a rushed 16:15 commit and a permanent disclosure, so
they check the two things that actually go wrong: a term hidden inside ordinary
code rather than sitting on its own line, and an owned term being treated as a leak.
"""

import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from tools import disclosure_gate

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def blocklist(tmp_path: Path) -> Path:
    """A two-tier blocklist in the same shape as the real one.

    Deliberately a local fixture rather than a read of the real file: these tests
    must not fail because someone edited the live blocklist, and the real file
    lives outside this repo.
    """
    content = textwrap.dedent(
        """\
        # Toast Sanitisation Blocklist

        Two tiers: the blocking sections below, and a final "Owned terms" section
        that is INFO only.

        Format:
        - `pattern` - suggested public-safe replacement - [category]

        ---

        ## Product and codename terms

        - `Zephyr Pay` - "a billing product I work on" or omit - [product name]

        ## Team and org terms

        - `deal-ledger` - "my work log" or omit - [internal tool]

        ## Owned terms - INFO only, never a block

        - `OPENKIT` - owned and publishable, INFO only - [John's own system]
        - `Openkit Bootstrap Framework` - owned and publishable, INFO only - [expanded form]
        """
    )
    path = tmp_path / "toast-blocklist.md"
    path.write_text(content)
    return path


@pytest.fixture
def staged(tmp_path: Path):
    """Copy a fixture out to a scratch dir before scanning it.

    The repo's own .disclosureignore exempts tests/fixtures/ - it has to, since
    those files exist to contain blocked terms. Once the gate learned to honour
    that ignore file for explicitly-named files too (QUAL-003), scanning a
    fixture in place correctly returned nothing. These tests are about scan
    behaviour, not repo layout, so they work on a copy.
    """

    def _staged(name: str) -> Path:
        target = tmp_path / name
        target.write_text((FIXTURES / name).read_text(encoding="utf-8"), encoding="utf-8")
        return target

    return _staged


def test_parses_both_tiers(blocklist: Path):
    blocking, owned = disclosure_gate.load_blocklist(blocklist)
    assert "Zephyr Pay" in blocking
    assert "deal-ledger" in blocking
    assert "OPENKIT" in owned
    # The owned tier must not bleed into the blocking tier - that is the whole
    # point of the second section.
    assert "OPENKIT" not in blocking


def test_flags_term_hidden_in_comment_and_path(blocklist: Path, staged):
    """T-01a: the realistic case - terms embedded in ordinary code, not bare."""
    findings = disclosure_gate.scan_path(staged("leaky_module.py"), blocklist)
    blocked = [f for f in findings if f.severity == "BLOCK"]
    terms = {f.term for f in blocked}

    assert "Zephyr Pay" in terms, "missed a term inside a code comment"
    assert "deal-ledger" in terms, "missed a term inside a path string"

    # Line numbers must point at the real occurrence - a finding you cannot
    # navigate to is a finding you will not fix at 16:15 on a deadline.
    zephyr_pay = next(f for f in blocked if f.term == "Zephyr Pay")
    assert zephyr_pay.line == 8, "Zephyr Pay sits in the comment on line 8"
    assert "billing product" in zephyr_pay.suggestion

    registry = next(f for f in blocked if f.term == "deal-ledger")
    assert registry.line == 9, "deal-ledger sits inside the path on line 9"


def test_owned_term_is_info_not_block(blocklist: Path, staged):
    findings = disclosure_gate.scan_path(staged("owned_only.py"), blocklist)
    assert findings, "an owned term must still be surfaced, not swallowed"
    assert all(f.severity == "INFO" for f in findings)
    assert {f.term for f in findings} >= {"OPENKIT"}


def test_clean_file_reports_nothing(blocklist: Path, staged):
    assert disclosure_gate.scan_path(staged("clean_module.py"), blocklist) == []


def test_format_example_in_preamble_is_not_a_term(blocklist: Path):
    """The blocklist documents its own format with a `pattern` placeholder.

    Found on the first real run: the parser ingested that documentation line as
    a real term, so every file containing the word "pattern" was reported as a
    leak. A gate that cries wolf on a common English word gets ignored, which is
    the failure mode that matters here.
    """
    blocking, _owned = disclosure_gate.load_blocklist(blocklist)
    assert "pattern" not in blocking
    assert "Zephyr Pay" in blocking, "the real terms must still parse"


def test_excluded_paths_are_skipped(blocklist: Path, tmp_path: Path):
    """Test fixtures deliberately contain blocked terms.

    Without exclusions the gate can never pass on its own repository, so it
    would be permanently ignored or permanently overridden - either way, not a
    gate.
    """
    tree = tmp_path / "repo"
    (tree / "tests" / "fixtures").mkdir(parents=True)
    (tree / "tests" / "fixtures" / "leak.py").write_text("# Zephyr Pay\n")
    (tree / "real.py").write_text("x = 1\n")

    assert disclosure_gate.scan_path(tree, blocklist), "sanity: unfiltered scan finds it"
    assert disclosure_gate.scan_path(tree, blocklist, exclude=["tests/fixtures/*"]) == []


# --- T-02a: the exit-code contract -------------------------------------------------


def run_cli(*args: str) -> subprocess.CompletedProcess:
    repo_root = Path(__file__).parent.parent
    return subprocess.run(
        [sys.executable, "-m", "tools.disclosure_gate", *args],
        capture_output=True,
        text=True,
        cwd=repo_root,
    )


def test_exit_non_zero_on_block(blocklist: Path, staged):
    result = run_cli(str(staged("leaky_module.py")), "--blocklist", str(blocklist))
    assert result.returncode == 1
    assert "BLOCK" in result.stdout


def test_exit_zero_when_only_info(blocklist: Path, staged):
    """An owned term must never change the verdict - visibility, not prevention."""
    result = run_cli(str(staged("owned_only.py")), "--blocklist", str(blocklist))
    assert result.returncode == 0
    assert "INFO" in result.stdout


def test_exit_zero_when_clean(blocklist: Path, staged):
    result = run_cli(str(staged("clean_module.py")), "--blocklist", str(blocklist))
    assert result.returncode == 0


def test_mode_work_allows_blocking_terms(blocklist: Path, staged):
    """The blocklist's own header says these are allowed in --mode work."""
    result = run_cli(
        str(staged("leaky_module.py")), "--blocklist", str(blocklist), "--mode", "work"
    )
    assert result.returncode == 0


def test_missing_blocklist_fails_loudly(tmp_path: Path, staged):
    """A gate that silently passes because it could not find its rules is worse
    than no gate - it produces false confidence before an irreversible action."""
    result = run_cli(str(staged("clean_module.py")), "--blocklist", str(tmp_path / "nope.md"))
    assert result.returncode == 2
    assert "not found" in (result.stdout + result.stderr).lower()


# ---------------------------------------------------------------------------
# Remediation tests - ship-plan Phase 3 review, 11 September
#
# Every test below encodes a case where the gate reported "Safe to publish."
# over something it was supposed to catch. They are grouped rather than
# scattered because they share one root cause: the gate had no way to tell
# "found nothing" apart from "looked at nothing".
# ---------------------------------------------------------------------------


def test_blocklist_parsing_to_zero_terms_fails_loudly(tmp_path: Path, staged):
    """SEC-002. The blocklist lives in another repo and can be reformatted without
    any commit here. When that happens the entry regex matches nothing, and the
    gate scans every file against an empty rule set and prints PASS."""
    drifted = tmp_path / "drifted.md"
    drifted.write_text(
        "# Blocklist\n\n## Product terms\n\n| term | replacement |\n|---|---|\n"
        "| Zephyr Pay | a billing product |\n",
        encoding="utf-8",
    )
    result = run_cli(str(staged("leaky_module.py")), "--blocklist", str(drifted))
    assert result.returncode == 2, (
        "a blocklist that parses to zero terms must fail to run, not pass:\n"
        + result.stdout
    )
    assert "0 term" in (result.stdout + result.stderr).lower()


def test_scanning_zero_files_fails_loudly(tmp_path: Path, blocklist: Path):
    """Committee must-fix 3. An empty scan and a clean scan printed the same
    verdict, so 'PASS' carried no evidence that any work happened."""
    empty = tmp_path / "empty_tree"
    empty.mkdir()
    result = run_cli(str(empty), "--blocklist", str(blocklist))
    assert result.returncode == 2, (
        "scanning zero files must fail to run, not pass:\n" + result.stdout
    )


def test_verdict_line_reports_counts(blocklist: Path, staged):
    """A PASS must say how many rules it applied and how many files it read, so
    a silently-empty run is visible in the output rather than only in a test."""
    result = run_cli(str(staged("clean_module.py")), "--blocklist", str(blocklist))
    assert result.returncode == 0
    assert "rule" in result.stdout.lower() and "file" in result.stdout.lower(), (
        "verdict line must report rule and file counts:\n" + result.stdout
    )


def test_credentials_tier_entries_are_parsed(tmp_path: Path):
    """Committee must-fix 1. The real blocklist phrases these as prose with the
    term in backticks partway through the line - `- Any absolute path starting
    with `/Homes/` - ...` - and the entry regex required a backtick immediately
    after "- ", so all four silently vanished. Six of ~40 rules never loaded."""
    real_shape = tmp_path / "credentials.md"
    real_shape.write_text(
        textwrap.dedent(
            """\
            # Blocklist

            ## Credentials and paths

            - Any string matching `ZKIA[0-9A-Z]{16}` - BLOCK (AWS access key) - [credential]
            - Any string matching `pat_[a-zA-Z0-9]{36}` - BLOCK (GitHub PAT) - [credential]
            - Any absolute path starting with `/Homes/` - BLOCK or generalise to `~/` - [PII path]
            - Any string matching email pattern with a `acmecorp.example` domain - BLOCK - [internal email]
            - `Some Term` - replacement text `(case-insensitive)` - [product name]
            """
        ),
        encoding="utf-8",
    )
    blocking, owned = disclosure_gate.load_blocklist(real_shape)
    assert len(blocking) == 5, f"expected 5 parsed rules, got {len(blocking)}: {list(blocking)}"
    assert "/Homes/" in blocking, (
        "the /Homes/ rule is the one that was live-leaking; it must parse"
    )
    assert "acmecorp.example" in blocking
    assert owned == {}


def test_absolute_home_path_is_blocked(tmp_path: Path):
    """The live false negative, reproduced. builder-plans/ carried 19 of these
    while the gate exited 0 with 'Safe to publish.'"""
    bl = tmp_path / "bl.md"
    bl.write_text(
        "# Blocklist\n\n## Credentials and paths\n\n"
        "- Any absolute path starting with `/Homes/` - BLOCK or generalise to `~/` - [PII path]\n"
        "- `Zephyr Pay` - a billing product - [product name]\n",
        encoding="utf-8",
    )
    leaky = tmp_path / "plan.md"
    leaky.write_text("- **Repo root**: `/Homes/someone/Projects/thing`\n", encoding="utf-8")
    result = run_cli(str(leaky), "--blocklist", str(bl))
    assert result.returncode == 1, "an absolute /Homes/ path must block:\n" + result.stdout


# Key-shaped strings are assembled at runtime, never written contiguously. The
# floor scans this repo like any other, so a literal here would block the suite's
# own source - the same reason tools/disclosure_gate.py splits its pattern
# prefixes. These are shapes, not keys: the AWS value is the one from Amazon's
# public documentation.
_AWS_KEY_SHAPE = "AKIA" + "IOSFODNN7EXAMPLE"
_GH_PAT_SHAPE = "ghp" + "_" + "a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5P6q7R8"


def test_secret_patterns_are_matched_as_regex(tmp_path: Path, blocklist: Path):
    """Committee must-fix 2. re.escape meant a credential pattern was searched as
    literal characters, so no secret *class* could ever match. The floor is
    hardcoded and non-overridable precisely so a blocklist edit cannot remove it."""
    leaky = tmp_path / "config.py"
    leaky.write_text(f'AWS_KEY = "{_AWS_KEY_SHAPE}"\n', encoding="utf-8")
    result = run_cli(str(leaky), "--blocklist", str(blocklist))
    assert result.returncode == 1, (
        "an AWS-key-shaped string must block regardless of the blocklist:\n" + result.stdout
    )


def test_github_pat_is_matched_as_regex(tmp_path: Path, blocklist: Path):
    leaky = tmp_path / "notes.md"
    leaky.write_text(f"token: {_GH_PAT_SHAPE}\n", encoding="utf-8")
    result = run_cli(str(leaky), "--blocklist", str(blocklist))
    assert result.returncode == 1, "a PAT-shaped string must block:\n" + result.stdout


def test_secret_floor_survives_an_empty_blocklist_section(tmp_path: Path, blocklist: Path):
    """The floor is the answer to 'what if someone edits the blocklist badly'.
    It must not be reachable through the blocklist at all."""
    assert _AWS_KEY_SHAPE[:4] not in blocklist.read_text(encoding="utf-8"), (
        "fixture blocklist must not itself contain the prefix, or this proves nothing"
    )
    leaky = tmp_path / "x.py"
    leaky.write_text(f'k = "{_AWS_KEY_SHAPE}"\n', encoding="utf-8")
    assert run_cli(str(leaky), "--blocklist", str(blocklist)).returncode == 1


def test_mode_work_cannot_waive_a_credential(tmp_path: Path, blocklist: Path):
    """Found by the eval committee on re-review, 2026-09-11.

    --mode work returned before the blocking check, and secret findings carry
    severity BLOCK like any other, so one flag disabled the floor the module
    docstring calls non-overridable. Internal vocabulary is waivable in work
    mode - that is the blocklist's own rule. A credential is not."""
    leaky = tmp_path / "conf.py"
    leaky.write_text(f'k = "{_AWS_KEY_SHAPE}"\n', encoding="utf-8")
    result = run_cli(str(leaky), "--blocklist", str(blocklist), "--mode", "work")
    assert result.returncode == 1, (
        "--mode work must not waive a credential:\n" + result.stdout
    )


def test_mode_work_still_waives_ordinary_internal_terms(tmp_path: Path, blocklist: Path, staged):
    """The fix must not turn --mode work into --mode public."""
    result = run_cli(
        str(staged("leaky_module.py")), "--blocklist", str(blocklist), "--mode", "work"
    )
    assert result.returncode == 0, result.stdout


def test_skip_dirs_tested_relative_to_scan_root(tmp_path: Path, blocklist: Path):
    """Committee must-fix 3, second half. _SKIP_DIRS tested absolute path parts,
    so a scan rooted anywhere under a directory named build/ or dist/ silently
    skipped every file in the tree and still printed PASS."""
    root = tmp_path / "build" / "project"
    root.mkdir(parents=True)
    (root / "leaky.py").write_text("# Zephyr Pay integration\n", encoding="utf-8")
    result = run_cli(str(root), "--blocklist", str(blocklist))
    assert result.returncode == 1, (
        "a scan root under a dir named 'build' must still scan its files:\n" + result.stdout
    )


def test_skip_dirs_still_skips_nested_build_dir(tmp_path: Path, blocklist: Path):
    """The fix must not remove the skipping - only re-anchor it to the scan root."""
    root = tmp_path / "project"
    (root / "build").mkdir(parents=True)
    (root / "build" / "generated.py").write_text("# Zephyr Pay\n", encoding="utf-8")
    (root / "real.py").write_text("x = 1\n", encoding="utf-8")
    result = run_cli(str(root), "--blocklist", str(blocklist))
    assert result.returncode == 0, "a nested build/ dir must still be skipped:\n" + result.stdout


def test_suppressed_files_are_reported(tmp_path: Path, blocklist: Path):
    """SEC-007. An over-broad .disclosureignore line was indistinguishable from a
    clean repo - the cheapest way to blind the gate is to exclude too much and
    never be told."""
    root = tmp_path / "repo"
    (root / "secrets").mkdir(parents=True)
    (root / "secrets" / "leak.py").write_text("# Zephyr Pay\n", encoding="utf-8")
    (root / "ok.py").write_text("x = 1\n", encoding="utf-8")
    (root / ".disclosureignore").write_text("secrets/*\n", encoding="utf-8")
    result = run_cli(str(root), "--blocklist", str(blocklist))
    assert result.returncode == 0
    assert "SUPPRESSED" in result.stdout, (
        "an excluded file must be named in the output:\n" + result.stdout
    )
    assert "secrets/leak.py" in result.stdout


def test_gate_scans_itself(blocklist: Path):
    """The scanner used to be excluded from its own scan - the one file in the
    repo nobody was checking."""
    ignore = Path(__file__).parent.parent / ".disclosureignore"
    text = ignore.read_text(encoding="utf-8")
    active = [ln.strip() for ln in text.splitlines() if ln.strip() and not ln.startswith("#")]
    assert "tools/disclosure_gate.py" not in active, (
        "the gate must not exclude itself from its own scan"
    )


def test_explicit_file_argument_honours_disclosureignore(tmp_path: Path, blocklist: Path):
    """QUAL-003 / ARCH-001. The gate only loaded .disclosureignore for directory
    targets, so naming a file directly bypassed it. The pre-commit hook scans one
    staged file at a time by explicit path - so an armed hook blocked on the very
    fixtures the ignore file exists to exempt, and the only way past was
    --no-verify, which trains the habit that kills the gate."""
    root = tmp_path / "repo"
    (root / "tests").mkdir(parents=True)
    leaky = root / "tests" / "fixture.py"
    leaky.write_text("# Zephyr Pay\n", encoding="utf-8")
    (root / ".disclosureignore").write_text("tests/*\n", encoding="utf-8")
    result = run_cli(str(leaky), "--blocklist", str(blocklist))
    assert result.returncode == 0, (
        "an explicitly-named ignored file must not block:\n" + result.stdout
    )
    assert "SUPPRESSED" in result.stdout, "and it must say so rather than passing silently"


def test_fully_suppressed_scan_is_not_an_empty_scan_error(tmp_path: Path, blocklist: Path):
    """Scanning nothing because everything was deliberately excluded is a reported
    state, not a broken run. Only an unexplained empty scan is an error."""
    root = tmp_path / "repo"
    (root / "skip").mkdir(parents=True)
    (root / "skip" / "a.py").write_text("x = 1\n", encoding="utf-8")
    (root / ".disclosureignore").write_text("skip/*\n", encoding="utf-8")
    result = run_cli(str(root), "--blocklist", str(blocklist))
    assert result.returncode == 0, result.stdout
    assert "SUPPRESSED" in result.stdout


def test_directory_scan_suppressing_everything_is_still_an_error(tmp_path: Path, blocklist: Path):
    """Found by adversarial self-review on 2026-09-11, and introduced by the fix
    for QUAL-003 the same day.

    Relaxing EmptyScanError to `files_scanned == 0 and not suppressed` was meant
    to let the pre-commit hook name a single exempt file without erroring. It also
    let a directory scan suppress EVERY file and report:

        38 rule(s) applied to 0 file(s). PASS   (exit 0)

    while a real leak sat in the tree. One over-broad ignore line - `*` - silently
    disarms the whole gate. Suppression EXPLAINS an empty directory scan; it does
    not make one safe. The distinction that matters is the target: a directory the
    gate was asked to check and checked nothing in is always an error, whereas a
    single explicitly-named file that is exempt is a legitimate no-op.
    """
    root = tmp_path / "repo"
    root.mkdir()
    (root / "leak.py").write_text("# Zephyr Pay\n", encoding="utf-8")
    (root / ".disclosureignore").write_text("*\n", encoding="utf-8")
    result = run_cli(str(root), "--blocklist", str(blocklist))
    assert result.returncode == 2, (
        "a directory scan that reached zero files must fail to run, however it got "
        "there:\n" + result.stdout
    )


def test_exclude_glob_cannot_disarm_a_directory_scan(tmp_path: Path, blocklist: Path):
    """Same hole, reached through --exclude rather than the ignore file."""
    root = tmp_path / "repo"
    root.mkdir()
    (root / "leak.py").write_text("# Zephyr Pay\n", encoding="utf-8")
    result = run_cli(str(root), "--blocklist", str(blocklist), "--exclude", "*")
    assert result.returncode == 2, result.stdout
