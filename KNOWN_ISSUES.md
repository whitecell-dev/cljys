# Known issues

Each entry names the assumption, the condition that breaks it, and what a user
sees today. "Loud" means non-zero exit or a compile error; it is a known gap,
not a silent wrong answer.

- **KNOWN [Recon §5]:** multi-arg `println` is emitted as one space-separated
  `say:` line. It works for numbers (`say: 1 2 3`) but YS rejects adjacent
  string literals (`say: 'a' 'b'`). *Fails when* a Clojure program prints two
  or more string literals in one call. *Surfaces as* a YS compile error, never
  a wrong print. Pinned by `multi_arg_print` for the working numeric case.

- **KNOWN [Recon §5]:** a keyword used as a value, or a variable key passed to
  `get`, is not translated into YS's map-key form. *Fails when* a program
  evaluates `:kw` on its own or calls `(get m k)` with a non-literal key.
  *Surfaces as* a YS error ("cannot be cast to Number" or an unresolved
  symbol), not a wrong value.

- **KNOWN [Recon §6]:** `TR01_simple`, `TR01_workflow` and `range_workflow`
  compare substrings, not exact output, and are frozen in their suite versions.
  *Fails when* an extra line is emitted around the matched substring; the
  probe still passes. *Surfaces as* no signal. Exact-output coverage for the
  same constructs is in v1.3.0 (`let_value_pos`) and v1.4.0.

- **KNOWN [Recon §4]:** a local run with the wrong `ys` version only warns and
  still writes evidence. *Fails when* the installed `ys` differs from
  `probes/manifest.json`'s pin; the JSON records the version, but a claim can
  cite it. *Surfaces as* a warning and a provenance entry, not a failure; CI
  uses `--strict`.

- **KNOWN [Recon §4]:** the transpiler is deterministic; the environment is
  not fully pinned. Python, locale and the `ys` build can differ. *Fails when*
  those differ from the run that produced a claim. *Surfaces as* a changed
  output with a recorded `python_version` / `ys_version` / transpiler hash in
  the evidence file.

- **KNOWN [Recon §6]:** mutation detection asserts each known defect's test
  fails; it does not prove the suite catches an arbitrary new defect. *Fails
  when* a mutation is not in `scripts/mutation_check.py`. *Surfaces as* an
  unfalsified green run for that shape.

- **KNOWN [Recon §4]:** the CI install pipes a release tarball from GitHub into
  `tar` without verifying a checksum. *Fails when* the release asset or its
  transport is substituted. *Surfaces as* whatever the substituted `ys` does;
  the recorded version string is not proof of provenance.

- **KNOWN [Recon §5]:** input validation is typed for the malformed forms
  covered by `scripts/check_input_boundary.py`; some other arity errors still
  raise an uncaught Python exception. *Fails when* a program uses an unsupported
  arity not in that list. *Surfaces as* a traceback and non-zero exit (loud),
  not a partial transform.
