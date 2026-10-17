#!/usr/bin/env python3
"""Prove the probe suite can actually detect a regression.

A probe suite that cannot fail is indistinguishable from one that cannot run.
This check re-introduces a known-fixed defect, asserts the probes go red, and
asserts they were green before it. Every fix claimed in REPORT.md should have a
mutation here.

    python3 scripts/mutation_check.py

Exit 0 only if every mutation was detected and every suite was green at rest.

The mutation is applied to a copy of the transpiler in a temp directory, never to
the tracked file, so this is safe to run in a working checkout with uncommitted
work in it. Evidence writing is off for the same reason: a mutated run would
otherwise overwrite convergence-claims/evidence/*.json with verdicts that the
next run has to rewrite again.
"""

import subprocess
import sys
import tempfile
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
    {
        "name": "mod-reverts-to-remainder",
        "file": "clj-to-ys.py",
        # OP_MAP, not RENAMES: `(mod a b)` dispatches through _infix at
        # clj-to-ys.py:812, so RENAMES' entry is shadowed for this path and a
        # mutation there would leave the suite green. Verified empirically.
        "find": '    "or": "||",\n    "mod": "%%",',
        "replace": '    "or": "||",\n    "mod": "%",',
        "must_fail": "v1.2.0",
        "why": "spec.md:141 and modulo-is-not-remainder.md: mod is floored (%%), rem is truncated (%); "
        "they agree on positive operands, so only a negative dividend separates them",
    },
    {
        "name": "let-binding-form-reverts-to-clojure",
        "file": "clj-to-ys.py",
        # Clojure's `name=init` binding form. YS wants name/value pairs, so this
        # does not change the value of anything - it makes the suite ERROR.
        "find": 'parts.append(f"{n} {v}")',
        "replace": 'parts.append(f"{n}={v}")',
        "must_fail": "v1.3.0",
        "why": "no-block-form-in-value-position.md: YS `let` accepts value position but "
        "requires name/value pairs; `[k=v]` is one form and is rejected",
    },
    {
        "name": "let-infix-body-unwrapped",
        "file": "clj-to-ys.py",
        # Reverts to the behavior that produced a SILENT wrong value rather than
        # an error: (let [n 3] n + 1) evaluates to 1 in YS, not 4.
        "find": "            if self._is_infix(body):",
        "replace": "            if False:  # mutated",
        "must_fail": "v1.3.0",
        "why": "an unparenthesized infix `let` body is evaluated as its last operand; "
        "only the wrap makes let_value_pos's `(let [x 1 y 2] (+ x y))` come out 3 "
        "instead of 2",
    },
    {
        "name": "map-keys-unquoted",
        "file": "clj-to-ys.py",
        # expr() on a keyword strips the colon, so this is the 014_maps defect
        # exactly: hash-map(a 1 b 2) makes YS resolve the keys as symbols.
        "find": '                if isinstance(k, Token) and k.kind == "KW":\n'
        '                    ks = \'"\' + k.val.lstrip(":") + \'"\'',
        "replace": "                ks = self.expr(k)",
        "must_fail": "v1.3.0",
        "why": "collection-literals-need-plus-prefix.md: a map literal has no flow-mapping "
        "form in YS code mode, so hash-map with QUOTED keys is the only form; an "
        "unquoted key is a symbol reference",
    },
]


def run_suite(version: str, transpiler: Path) -> tuple[int, str]:
    done = subprocess.run(
        [
            sys.executable,
            str(RUNNER),
            "--suite",
            version,
            "--transpiler",
            str(transpiler),
            "--no-evidence",
        ],
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

    with tempfile.TemporaryDirectory() as tmpdir:
        for mutation in MUTATIONS:
            name = mutation["name"]
            suite = mutation["must_fail"]
            target = ROOT / mutation["file"]
            # Mutate a copy. Nothing tracked is touched, so there is nothing to
            # restore and the check is green-then-red rather than green-red-green.
            mutated = Path(tmpdir) / target.name
            mutated.write_text(target.read_text())

            code, out = run_suite(suite, target)
            if code != 0:
                print(f"SKIP {name}: {suite} is not green at rest, cannot show a transition")
                print("     " + out.strip().replace("\n", "\n     "))
                failures.append(name)
                continue
            print(f"  baseline {suite}: green")

            apply(mutated, mutation["find"], mutation["replace"])
            code, out = run_suite(suite, mutated)
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

    print()
    if failures:
        print(f"mutation check FAILED: {', '.join(failures)}")
        return 1
    print(f"mutation check passed: {len(MUTATIONS)} mutation(s) detected")
    return 0


if __name__ == "__main__":
    sys.exit(main())