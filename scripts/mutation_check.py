#!/usr/bin/env python3
"""Prove the probe suite can actually detect a regression.

A probe suite that cannot fail is indistinguishable from one that cannot run.
This check re-introduces a known-fixed defect, asserts the probes go red, then
restores the file and asserts they go green again. Every fix claimed in
REPORT.md should have a mutation here.

    python3 scripts/mutation_check.py

Exit 0 only if every mutation was detected and every revert restored cleanly.
Intended for CI, where the checkout is disposable; it does edit a tracked file
in place and relies on its own restore, not on git.
"""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNNER = ROOT / "probes" / "run_probes.py"

# Each mutation must be a single, exact, unambiguous string in the named file:
# the smallest edit that reinstates a defect this repo has already fixed.
MUTATIONS = [
    {
        "name": "range-end-becomes-inclusive",
        "file": "clj-to-ys.py",
        # The 2-arg case only. The 3-arg line shares this prefix, so match the
        # whole line to avoid also producing `(1 .. 10, 2)`.
        "find": 'return f"range({self.expr(form[1])}, {self.expr(form[2])})"',
        "replace": 'return f"({self.expr(form[1])} .. {self.expr(form[2])})"',
        # v1.1.0 is the suite the range fix introduced and is green at rest.
        # v1.0.0 is already red (TR01_workflow), so it cannot show a transition.
        "must_fail": "v1.1.0",
        "why": "REPORT.md section 10: `(a .. b)` is inclusive in YS, `(range a b)` is not",
    },
]


def run_suite(version: str) -> tuple[int, str]:
    done = subprocess.run(
        [sys.executable, str(RUNNER), "--suite", version],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        cwd=str(ROOT),
    )
    return done.returncode, done.stdout


def apply(path: Path, find: str, replace: str) -> None:
    original = path.read_text()
    if original.count(find) != 1:
        raise SystemExit(
            f"mutation anchor is not unique in {path.name}: found "
            f"{original.count(find)} occurrences of {find!r}"
        )
    path.write_text(original.replace(find, replace))


def main() -> int:
    if not RUNNER.is_file():
        sys.exit(f"missing {RUNNER}")
    failures = []

    for mutation in MUTATIONS:
        name = mutation["name"]
        suite = mutation["must_fail"]
        path = ROOT / mutation["file"]
        original = path.read_text()

        code, out = run_suite(suite)
        if code != 0:
            print(f"SKIP {name}: {suite} is not green at rest, cannot show a transition")
            print("     " + out.strip().replace("\n", "\n     "))
            failures.append(name)
            continue
        print(f"  baseline {suite}: green")

        try:
            apply(path, mutation["find"], mutation["replace"])
            code, out = run_suite(suite)
            if code == 0:
                print(f"FAIL {name}: probes stayed GREEN with the defect reintroduced")
                failures.append(name)
            else:
                failed = [
                    line.split()[1]
                    for line in out.splitlines()
                    if line.strip().startswith(("FAIL", "ERROR"))
                ]
                print(f"  mutated  {suite}: red ({', '.join(failed) or 'exit non-zero'})")
                print(f"  detected: {mutation['why']}")
        finally:
            path.write_text(original)

        code, out = run_suite(suite)
        if code != 0:
            print(f"FAIL {name}: suite did not return to green after restore")
            failures.append(name)
        else:
            print(f"  restored {suite}: green")

    print()
    if failures:
        print(f"mutation check FAILED: {', '.join(failures)}")
        return 1
    print(f"mutation check passed: {len(MUTATIONS)} mutation(s) detected and reverted")
    return 0


if __name__ == "__main__":
    sys.exit(main())