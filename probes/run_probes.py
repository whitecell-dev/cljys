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
retire the entry.

Evidence lands in convergence-claims/evidence/run-<suite version>.json, and is
rewritten only when something other than the timestamp changed, so a clean
re-run leaves the working tree clean.
"""

import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = Path(__file__).resolve().parent / "manifest.json"
EVIDENCE = ROOT / "convergence-claims" / "evidence"


def load_manifest() -> dict:
    if not MANIFEST.is_file():
        sys.exit(f"missing {MANIFEST}")
    return json.loads(MANIFEST.read_text())


def ys_version() -> str | None:
    """Installed `ys` version, or None if it is not on PATH."""
    try:
        out = subprocess.run(
            ["ys", "--version"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
        ).stdout
    except FileNotFoundError:
        return None
    for token in out.split():
        if token[0].isdigit():
            return token
    return None


def transpile(corpus: Path, transpiler: Path) -> tuple[str | None, str]:
    """Clojure -> YS via the transpiler. Returns (ys_code, error)."""
    result = subprocess.run(
        [sys.executable, str(transpiler), str(corpus)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=str(ROOT),
    )
    if not result.stdout:
        return None, result.stderr.strip() or "transpiler produced no output"
    return result.stdout, None


def run_ys(ys_code: str, invoke: str) -> tuple[str, str]:
    """Execute generated YS. `invoke` selects the run/print distinction."""
    with tempfile.NamedTemporaryFile("w", suffix=".ys", delete=False) as handle:
        handle.write(ys_code)
        tmp = Path(handle.name)
    try:
        cmd = ["ys", "-p", str(tmp)] if invoke == "print" else ["ys", str(tmp)]
        done = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=str(ROOT)
        )
        return done.stdout, done.stderr
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
        record["expected"] = "xfail"
        record["status"] = "XPASS" if record["status"] == "PASS" else "XFAIL"
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
    }
    for path in (corpus, expected_path):
        if not path.is_file():
            record["error"] = f"missing {path.relative_to(ROOT)}"
            return record

    source = corpus.read_text()
    record["input"] = source
    ys_code, error = transpile(corpus, transpiler)
    if ys_code is None:
        record["error"] = error
        return record

    actual, ys_err = run_ys(ys_code, probe["invoke"])
    if ys_err.strip():
        record["error"] = f"ys failed: {ys_err.strip()}"
        return record

    expected_doc = json.loads(expected_path.read_text())
    passed, diff = compare(actual, expected_doc)
    record["expected_output"] = expected_doc
    record["actual_output"] = actual
    record["diff"] = diff
    record["status"] = "PASS" if passed else "FAIL"
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
        have = json.loads(out.read_text())
        if {k: v for k, v in have.items() if k != "timestamp"} == wanted:
            return False
    out.write_text(json.dumps(results, indent=2) + "\n")
    return True


def run_suite(suite: dict, transpiler: Path, evidence: bool) -> dict:
    results = {
        "probe_suite_version": suite["version"],
        "corpus_version": suite["corpus_version"],
        "expected_version": suite["expected_version"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
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
        print("ERROR: `ys` is not on PATH; no probe can be verified.")
        print("  install with: pip install yamlscript==%s" % manifest["ys_version"])
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
            for verdict in ("PASS", "FAIL", "ERROR", "XFAIL", "XPASS")
        }
        print(
            "{}: {} PASS, {} FAIL, {} ERROR, {} XFAIL, {} XPASS".format(
                suite["version"],
                counts["PASS"],
                counts["FAIL"],
                counts["ERROR"],
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
        bad += counts["FAIL"] + counts["ERROR"] + counts["XPASS"]
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())