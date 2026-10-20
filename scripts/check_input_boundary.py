#!/usr/bin/env python3
"""Assert that malformed Clojure is rejected with a typed code, not repaired.

Run: python3 scripts/check_input_boundary.py
Exit 0 when every case matches; 1 otherwise. No test framework, no fixtures.
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRANSPILER = ROOT / "clj-to-ys.py"

CASES = [
    ("(def x \\a)", "E_UNKNOWN_CHAR"),
    ('(println "oops)', "E_UNTERMINATED_STRING"),
    ('(println #"oops)', "E_UNTERMINATED_REGEX"),
    ("(println 1", "E_UNCLOSED_FORM"),
    (")", "E_UNEXPECTED_CLOSE"),
    ("'", "E_MISSING_FORM"),
    ("(let [x] x)", "E_ODD_BINDINGS"),
    ("(doseq [x] x)", "E_ODD_BINDINGS"),
    ("{:a}", "E_ODD_MAP"),
    ("(defn f [x &] x)", "E_BAD_PARAM"),
]


def run(source: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(TRANSPILER), "-"],
        input=source,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=str(ROOT),
    )


def main() -> int:
    failures = 0
    for source, code in CASES:
        done = run(source)
        expected = f"ERROR[{code}]:"
        if done.returncode != 2 or expected not in done.stderr:
            failures += 1
            print(
                f"FAIL {source!r}: expected rc=2 and {expected!r}, "
                f"got rc={done.returncode} stderr={done.stderr.strip()!r}"
            )

    valid = run('(println "ok")')
    if valid.returncode != 0 or "say:" not in valid.stdout:
        failures += 1
        print(
            f"FAIL valid input: expected rc=0 and emitted say:, "
            f"got rc={valid.returncode} stdout={valid.stdout.strip()!r}"
        )

    print(f"{len(CASES) + 1 - failures}/{len(CASES) + 1} input-boundary checks passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
