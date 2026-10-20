#!/usr/bin/env python3
"""Probe orchestrator for cljys.

Runs every probe declared in probes/manifest.json, independently of the
transpiler's own parser, assumptions, or validation, and writes one evidence
file per suite.

    python3 probes/run_probes.py                  # all suites
    python3 probes/run_probes.py --suite v1.1.0   # one suite

    --transpiler PATH   transpile with this file instead of clj-to-ys.py
                        (scripts/mutation_check.py points this at a copy)
    --no-evidence       run the probes, write nothing
    --strict            fail instead of warning when the installed `ys` is not
                        the pinned version. Local runs warn; CI passes this.

Exit code is 0 only when every probe in every selected suite passes and no xfail
probe unexpectedly passes, so CI can gate on it directly. A probe marked
`"status": "xfail"` in the manifest is expected to fail: it reports XFAIL while
it does, XPASS when it stops, and XPASS is an error - that is the signal to
retire the entry. A probe that times out is UNKNOWN, never XFAIL: it says
nothing about the defect.

Every verdict carries a typed `reason` and the exit codes that produced it. The
evidence file records the interpreter version, the installed `ys` version, and
the SHA-256 of the transpiler, so a PASS is bound to the code and runtime that
produced it. It is rewritten only when something other than the timestamp
changed, so a clean re-run leaves the working tree clean; the timestamp is the
last *content change*, not the last run.
"""

import hashlib
import json
import os
import platform
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = Path(__file__).resolve().parent / "manifest.json"
EVIDENCE = ROOT / "convergence-claims" / "evidence"

# A hung transpiler or interpreter is not a verdict. It is UNKNOWN, and the run
# fails without pretending the probe passed or failed.
TIMEOUT = 60


def load_manifest() -> dict:
    if not MANIFEST.is_file():
        sys.exit(f"missing {MANIFEST}")
    return json.loads(MANIFEST.read_text())


def ys_version() -> str | None:
    """Installed `ys` version, or None if it is not on PATH or not runnable."""
    try:
        done = subprocess.run(
            ["ys", "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if done.returncode != 0:
        return None
    for token in done.stdout.split():
        if token[0].isdigit():
            return token
    return None


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def transpile(corpus: Path, transpiler: Path) -> tuple[str | None, str, dict]:
    """Clojure -> YS via the transpiler. Returns (ys_code, error, details)."""
    details = {"transpiler_exit_code": None, "reason": None}
    try:
        result = subprocess.run(
            [sys.executable, str(transpiler), str(corpus)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=str(ROOT),
            timeout=TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        details["reason"] = "transpiler_timeout"
        return None, f"transpiler timed out after {TIMEOUT}s", details
    details["transpiler_exit_code"] = result.returncode
    if result.returncode != 0:
        details["reason"] = "transpiler_error"
        return None, result.stderr.strip() or f"transpiler exited {result.returncode}", details
    if not result.stdout:
        details["reason"] = "transpiler_no_output"
        return None, result.stderr.strip() or "transpiler produced no output", details
    return result.stdout, None, details


def run_ys(ys_code: str, invoke: str) -> tuple[str, str, int | None, bool]:
    """Execute generated YS.

    Returns (stdout, stderr, exit_code, timed_out). The caller decides the
    verdict; an exit code is not discarded, and a timeout is UNKNOWN rather
    than FAILED.
    """
    with tempfile.NamedTemporaryFile("w", suffix=".ys", delete=False) as handle:
        handle.write(ys_code)
        tmp = Path(handle.name)
    try:
        cmd = ["ys", "-p", str(tmp)] if invoke == "print" else ["ys", str(tmp)]
        done = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=str(ROOT),
            timeout=TIMEOUT,
        )
        return done.stdout, done.stderr, done.returncode, False
    except subprocess.TimeoutExpired:
        return "", "", None, True
    finally:
        tmp.unlink(missing_ok=True)


def compare(actual: str, expected_doc: dict) -> tuple[bool, dict | None]:
    """Exact or substring match, decided by the expected file's own shape."""
    if "expected_output_contains" in expected_doc:
        wanted = expected_doc["expected_output_contains"]
        missing = [c for c in wanted if c not in actual]
        passed = not missing
        diff = None if passed else {"expected_contains": wanted, "missing": missing, "actual": actual}
    else:
        wanted = expected_doc["expected_output"]
        passed = actual == wanted
        diff = (
            None
            if passed
            else {
                "expected": wanted,
                "actual": actual,
                "expected_repr": repr(wanted),
                "actual_repr": repr(actual),
            }
        )
    return passed, diff


def run_probe(probe: dict, suite_version: str, transpiler: Path) -> dict:
    record = _run_probe(probe, suite_version, transpiler)
    if probe.get("status") == "xfail":
        # A known defect, kept under observation: failing is the expected
        # verdict, passing means the defect is gone and the entry is stale.
        # An UNKNOWN (timeout) is not a failure and must not be laundered into
        # XFAIL - it says nothing about the defect.
        record["expected"] = "xfail"
        if record["status"] == "PASS":
            record["status"] = "XPASS"
        elif record["status"] in ("FAIL", "ERROR"):
            record["status"] = "XFAIL"
    return record


def _run_probe(probe: dict, suite_version: str, transpiler: Path) -> dict:
    probe_id = probe["id"]
    corpus = ROOT / probe["corpus"]
    expected_path = ROOT / probe["expected"]
    record = {
        "probe_id": probe_id,
        "suite": suite_version,
        "kind": probe.get("kind"),
        "status": "ERROR",
        "reason": None,
    }
    for path in (corpus, expected_path):
        if not path.is_file():
            record["reason"] = "missing_file"
            record["error"] = f"missing {path.relative_to(ROOT)}"
            return record

    source = corpus.read_text()
    record["input"] = source
    ys_code, error, details = transpile(corpus, transpiler)
    record.update(details)
    if ys_code is None:
        record["error"] = error
        return record

    actual, ys_err, ys_rc, timed_out = run_ys(ys_code, probe["invoke"])
    record["ys_exit_code"] = ys_rc
    if timed_out:
        record["status"] = "UNKNOWN"
        record["reason"] = "ys_timeout"
        record["error"] = f"ys timed out after {TIMEOUT}s"
        return record
    if ys_rc != 0:
        record["status"] = "ERROR"
        record["reason"] = "ys_error"
        record["error"] = f"ys exited {ys_rc}: {ys_err.strip() or '(no stderr)'}"
        return record
    if ys_err.strip():
        record["status"] = "ERROR"
        record["reason"] = "ys_stderr"
        record["error"] = f"ys wrote to stderr: {ys_err.strip()}"
        return record

    expected_doc = json.loads(expected_path.read_text())
    passed, diff = compare(actual, expected_doc)
    record["expected_output"] = expected_doc
    record["actual_output"] = actual
    record["diff"] = diff
    record["status"] = "PASS" if passed else "FAIL"
    record["reason"] = None if passed else "output_mismatch"
    record["passed"] = passed
    return record


def write_evidence(results: dict, out: Path) -> bool:
    """Write the evidence file unless everything but the timestamp is unchanged.

    Evidence is tracked on purpose (CODING_STANDARDS.md rule 10), so rewriting
    it on every run would leave a dirty working tree after every probe run for
    nothing. Returns True if the file was written.
    """
    wanted = {k: v for k, v in results.items() if k != "timestamp"}
    if out.is_file():
        try:
            have = json.loads(out.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            print(f"WARNING: {out.name} was unreadable ({exc}); rewriting", file=sys.stderr)
            have = None
        if have is not None and {k: v for k, v in have.items() if k != "timestamp"} == wanted:
            return False
    tmp = out.with_name(out.name + ".tmp")
    tmp.write_text(json.dumps(results, indent=2) + "\n")
    os.replace(tmp, out)
    return True


def run_suite(suite: dict, transpiler: Path, evidence: bool) -> dict:
    results = {
        "probe_suite_version": suite["version"],
        "corpus_version": suite["corpus_version"],
        "expected_version": suite["expected_version"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "provenance": {
            "ys_version": ys_version(),
            "python_version": platform.python_version(),
            "transpiler": str(transpiler.relative_to(ROOT))
            if transpiler.is_relative_to(ROOT)
            else str(transpiler),
            "transpiler_sha256": sha256(transpiler),
        },
        "probes": [
            run_probe(p, suite["version"], transpiler) for p in suite["probes"]
        ],
    }
    if evidence:
        EVIDENCE.mkdir(parents=True, exist_ok=True)
        write_evidence(results, EVIDENCE / f"run-{suite['version']}.json")
    return results


def main() -> int:
    args = sys.argv[1:]
    manifest = load_manifest()

    installed = ys_version()
    if installed is None:
        print("ERROR: `ys` is not on PATH or is not runnable; no probe can be verified.")
        print("  install the release asset described in README.md 'Running Things'")
        print("  (the PyPI `yamlscript` package does not ship the `ys` CLI)")
        return 2
    if installed != manifest["ys_version"]:
        mismatch = (
            f"manifest pins ys {manifest['ys_version']}, found {installed}."
            " Evidence is not comparable across versions."
        )
        # A local run on the wrong version is worth a warning; CI evidence that
        # silently differs from the pin is not, so CI passes --strict.
        if "--strict" in args:
            print("ERROR: " + mismatch)
            return 2
        print("WARNING: " + mismatch)

    transpiler = ROOT / "clj-to-ys.py"
    if "--transpiler" in args:
        transpiler = Path(args[args.index("--transpiler") + 1]).resolve()
        if not transpiler.is_file():
            sys.exit(f"missing transpiler {transpiler}")
    evidence = "--no-evidence" not in args

    suites = manifest["suites"]
    if "--suite" in args:
        wanted = args[args.index("--suite") + 1]
        suites = [s for s in suites if s["version"] == wanted]
        if not suites:
            print(f"no such suite: {wanted}")
            return 2

    bad = 0
    for suite in suites:
        results = run_suite(suite, transpiler, evidence)
        counts = {
            verdict: sum(1 for p in results["probes"] if p["status"] == verdict)
            for verdict in ("PASS", "FAIL", "ERROR", "UNKNOWN", "XFAIL", "XPASS")
        }
        print(
            "{}: {} PASS, {} FAIL, {} ERROR, {} UNKNOWN, {} XFAIL, {} XPASS".format(
                suite["version"],
                counts["PASS"],
                counts["FAIL"],
                counts["ERROR"],
                counts["UNKNOWN"],
                counts["XFAIL"],
                counts["XPASS"],
            )
        )
        for probe in results["probes"]:
            if probe["status"] != "PASS":
                print(f"  {probe['status']:5} {probe['probe_id']}")
                if probe.get("error"):
                    print(f"        {probe['error'].splitlines()[0]}")
                if probe["status"] == "XPASS":
                    print(
                        "        expected to fail but passed: retire the xfail"
                        " in probes/manifest.json"
                    )
        if evidence:
            name = f"run-{suite['version']}.json"
            print(f"  evidence: {(EVIDENCE / name).relative_to(ROOT)}")
        bad += counts["FAIL"] + counts["ERROR"] + counts["UNKNOWN"] + counts["XPASS"]
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())