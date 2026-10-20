# REPORT: Three-Layer Environment for cljys

> **Staleness banner.** This file is hand-written and nothing regenerates it.
> Where it states probe counts, those figures describe the v1.0.0-era run cited
> in the section and are **not** the current verdicts — the evidence files in
> `convergence-claims/evidence/` are the record, and they churn on every run.
> Sections 6 and 7 additionally contain claims that were never backed by a
> test; those are marked inline as FALSE/UNTESTED rather than deleted, because
> the record of having asserted them is part of this repo's research history.
> Section 11 contained a claim of the same kind — that the CI gate executes —
> which was **retracted on 2026-10-17** and is marked in place. See `README.md`
> § "Notes on the Reports".

## 1. Composition Enumeration (Step 1)

### 1.1 Primitives in isolation

| composition id | primitives involved | source | why it matters |
|---|---|---|---|
| P01 | def, assignment (numbers, strings, vectors) | test_primitives/test_assignment.clj, test_suite/001_basic_assignment.clj | basic binding |
| P02 | arithmetic (+, *, mod/rem) | test_suite/002_arithmetic.clj | numeric operations |
| P06 | each/doseq (basic iteration) | test_primitives/each.clj, test_suite/006_loops_each.clj | iteration primitive |
| P11 | range | test_primitives/test_loop.clj | sequence generation - critical |
| P12 | threading (->) | test_primitives/test_threading.clj, test_suite/012_threading.clj | pipeline composition |

### 1.2 Pairs of primitives that appear together

| composition id | primitives involved | source | why it matters |
|---|---|---|---|
| PA01 | doseq + range (nested) | test_primitives/test_loop.clj | nested iteration with range |

### 1.3 Triples and larger compositions

| composition id | primitives involved | source | why it matters |
|---|---|---|---|
| TR01_simple | json/load + def + say + get + count + str | test_queries/find_dependents.clj (simplified) | workflow query shape |
| TR02 | doseq + range (nested) + arithmetic + println | test_primitives/test_loop.clj line 2 | range composition case |

### 1.4 Specific range bug composition (exact as it appeared)

| composition id | primitives involved | source | why it matters |
|---|---|---|---|
| BUG01 | doseq (nested, 2 levels) + range + arithmetic (* i j) + println | test_primitives/test_loop.clj line 2 | Canonical case: A+B+C produces wrong program. Correct Clojure semantics require range(a,b) to be exclusive of end. |


## 2. Probe Suite (Step 2)

### 2.1 Probe Structure
- Probe suite version: v1.0.0
- Corpus version: v1.0.0  
- Expected outputs version: v1.0.0
- All probes are independently verifiable (no use of cljys internals, direct comparison of actual vs independently derived expected outputs)
- Each probe produces: input, expected_output, actual_output, diff (when failing)

### 2.2 Probe Inventory

| probe_id | type | checks | status (v1.0.0 run of 2026-10-05, see banner) |
|---|---|---|---|
| BUG01 | composition | nested doseq with range - correct Clojure semantics (range exclusive of end) | FAIL |
| PA01 | composition | doseq + range pair | FAIL |
| TR02 | composition | nested range composition | FAIL |
| P01_def | primitive | basic def assignments (no output) | PASS |
| P02_arithmetic | primitive | arithmetic operations | PASS |
| P06_each | primitive | each iteration over vector | PASS |
| P11_range | primitive | range produces exclusive end (Clojure semantics) | FAIL |
| P12_threading | primitive | threading macro (->) | PASS |
| TR01_simple | workflow | realistic query shape execution | PASS |

### 2.3 Verification of Failure Detection
All probes were verified to fail when given deliberately incorrect expected outputs (Step 2 gate satisfied). Probes never assume cljys correctness.


## 3. Probe Suite Run Against cljys (Step 3)

- Run: run-v1.0.0.json (2026-10-05T05:08:21.208012Z)
- Summary: 5 PASS, 5 FAIL, 0 ERROR
- **Historical.** This counts a superseded local run, not the committed
  `convergence-claims/evidence/run-v1.0.0.json`, which records different
  verdicts. For the record as of 2026-10-17 all four suites are green —
  10, 5, 2 and 3 PASS across v1.0.0 to v1.3.0, `make counts` — and `TR01_workflow`
  is one of the ten, not an ERROR. Read the
  evidence file for current truth.
- Primitives in isolation: P01_def, P02_arithmetic, P06_each, P12_threading PASS (4/5 primitive probes pass). P11_range FAILS due to range mapping bug (emits `(1 .. 4)` instead of correct range semantics).
- Compositions: All composition probes involving range (BUG01, PA01, TR02) FAIL. The range bug composition (BUG01) fails as predicted - actual output has 12 lines vs expected 6 lines due to wrong iteration bounds.
- Workflow probes: TR01_simple PASS (partial workflow execution succeeds).
- Evidence is stored as raw JSON with full diffs in `convergence-claims/evidence/run-v1.0.0.json`.


## 4. Workflow-Level Claim (Step 4)

The Convergence claim is defined in `convergence-claims/cljys-calyx-query.md`:

```markdown
- id: cljys-calyx-query
- version: v1.0.0
- scope: cljys.calyx-query
- claim: >
  cljys version X is authorized for CALYX query pipelines,
  valid while probe suite Y passes on corpus Z.
  Exploratory queries only. Production use requires a
  separate authorization.
- constraint: exploratory queries only
- drift_condition: probe suite must pass without regression
- evidence_refs:
  - probes/run-v1.0.0.json (specific run with timestamp)
  - References to specific probe IDs (compositions/BUG01, PA01, TR02; primitives/P01_def, P02_arithmetic, P06_each, P11_range, P12_threading; workflows/TR01_simple)
- current state: SUSPECT (based on latest probe run showing failures)
```

The claim is workflow-scoped (not per-primitive), and it references a specific probe run (run-v1.0.0.json) with concrete evidence - not the probe suite in the abstract. This satisfies the gate in Step 4.


## 5. CI Binding (Step 5)

CI configuration in `.github/workflows/probe.yml`:
- Runs probe suite on push/PR to main/master
- Executes `python3 probes/run_probes.py --strict`
- If all probes pass (exit code 0), claim state becomes ACTIVE
- If any probe fails (non-zero exit), claim state becomes SUSPECT
- Uploads probe results as artifacts
- Also runs the mutation check and `run_tests.sh`, both gating

The state transition is mechanical - no human in the loop. The binding keeps the claim current based on probe results.

**What is actually mechanical (verified in `.github/workflows/probe.yml`):** a
failing suite fails the job, and the job publishes `claim_state` as an output.
**What is not established:** that any of it has ever run. The workflow could not
install `ys` until 2026-10-17 (see §11's retraction), and no run of it has been
observed since. Treat the binding as correct-by-inspection, not verified.

**What is NOT established:** "Gate test performed" below was written as though a
CHALLENGE-path test had run. No such test exists in this repository. There is no
`can_proceed`, no worker, and no test file implementing section 6. The
transition is a guard in a CI job that nothing in-repo consumes; treat
"downstream workers stop" as untested.


## 6. CHALLENGE Path Test (Step 6)

> **FALSE — no such test exists.** This section originally claimed
> "Test results: **PASSED**". Nothing in the tree implements the CHALLENGE path
> and no test exercises it. The original text is retained below as a record of
> what was claimed; it is not evidence. `README.md` § "Safety Claims vs Ground
> Truth" tracks this as a standing false claim.

The CHALLENGE path would simulate:
1. Probe suite passes → claim is ACTIVE
2. Downstream worker relies on claim → can proceed (worker.can_proceed() returns True)
3. Something changes (environment/cljys/corpus) → probe suite fails → claim becomes SUSPECT  
4. Downstream worker stops → cannot proceed (worker.can_proceed() returns False)

Test results: **NOT RUN — no such test exists.**

Steps 1 and 3 correspond to real CI logic (`.github/workflows/probe.yml:75-84`,
`:86-91`).
Steps 2 and 4 have no implementation in this repository: the downstream worker
does not exist here, so its behavior cannot have been verified.


## 7. What This Environment Enables

- **Bounded trust**: Instead of "cljys is correct", we can state "cljys version X is authorized for CALYX query pipelines, valid while probe suite Y passes on corpus Z" - trust is scoped and conditional.
- **Separation of concerns**: Facts live in probes (independent verification), decisions live in Convergence claims. These are not conflated.
- **Early detection of composition bugs**: The probe suite catches cases where individual constructs work but compositions produce wrong programs (e.g., the range bug case).
- **Mechanical enforcement**: When probes fail, CI fails the job and the claim becomes SUSPECT. What happens *after* that is untested - no downstream worker exists in this repository, so "workers stop" is not demonstrated (section 6).
- **Reproducible evidence**: Each probe run produces concrete, versioned evidence with full inputs, outputs, and diffs.
- **Additive verification**: The probe suite is additive and frozen once written (with versioning). Changes require new probe versions.

## 8. What This Environment Still Doesn't Cover

- **Does not fix cljys**: The probes reveal bugs but don't repair the underlying transpiler. Many composition probes fail due to the range mapping issue.
- **Limited corpus coverage**: The current probe suite covers the range bug and a few primitives/workflows, but not all enumerated compositions from Step 1 (e.g., PA03, TR03, TR04 not fully implemented as executable probes in this iteration).
- **YS execution semantics**: The verification relies on running transpiled YS through `ys` - differences in YS runtime behavior could affect results.
- **Non-deterministic cases**: All current probes are deterministic; non-deterministic behavior is not covered.
- **Performance/edge cases**: Large inputs, resource constraints, etc. are not covered by the current corpus.

## 9. Definition of Done

- [x] `probes/` with versioned suite (v1.0.0), corpus (v1.0.0), and expected outputs (v1.0.0)
- [x] `convergence-claims/cljys-calyx-query.md` with specific evidence reference to run-v1.0.0.json
- [x] `.github/workflows/probe.yml` that binds probe results to claim state (mechanical transition)
- [x] `REPORT.md` with enumeration, probe results, claim, and CI
- [ ] ~~CHALLENGE path stops worker~~ — retracted; no such test exists (section 6)

The three-layer environment is built. The probe suite correctly identifies that while many primitives work, compositions involving the range mapping issue produce incorrect programs. This matches the experimental findings described in the task.

The CHALLENGE-path item above was previously checked off as satisfied. It is
unretracted here rather than simply unchecked because the gap is a real one:
this repo has a guard that fails CI, not a verified end-to-end stop.

## 10. Range Bug Fix (Follow-up)

**Root cause:** The transpiler emitted YS range syntax `(a .. b)` for Clojure `(range ...)`, but in YAMLScript `(a .. b)` is inclusive of the end while Clojure `(range a b)` is exclusive. Also 1-arg and 3-arg forms were mishandled. The fix changes range emission to use YS's `range()` function form (`range(a,b)`, `range(0,n)`, `range(a,b,step)`) which matches Clojure's semantics (exclusive end).

**Verification:**
- v1.0.0 suite: 9 PASS, 1 ERROR (TR01_workflow, unrelated to range — the `let` defect, since fixed on 2026-10-17; the suite is now 10 PASS). The 4 range-related failures (BUG01, P11_range, PA01, TR02) all flip to PASS.
- v1.1.0 suite (new probes including range 1/2/3-arg, nested, and range-using workflow): 5 PASS, 0 FAIL.
- Mutation check: reverted fix → probes go red; reapplied fix → probes go green. Confirms the fix is causal.
- v1.0.0 corpus/expected remain frozen; v1.1.0 adds additional probes without modifying existing ones.

## 11. Verification Environment Hardening (Follow-up)

Sections 5 and 6 described a mechanical SUSPECT transition. It had never
actually executed: the gate was decorative.

### Defects found in the gate

| Defect | Location | Effect |
|---|---|---|
| workflow not in `.github/workflows/` | `ci/probe.yml` | GitHub Actions only discovers workflows in `.github/workflows/`, so the suite had never run in CI at all |
| `ys` never installed in CI | `.github/workflows/probe.yml` | every probe would ERROR on a runner. Fixed twice: first by adding a `pip install yamlscript` step, then again when that step was found to install the wrong artifact — see the retraction below |
| `$?` read after `\| tee` | `.github/workflows/probe.yml` | captured `tee`'s status, always `0`; verified: runner exits 1, old logic reports `EXIT_CODE=0` |
| `continue-on-error: true` | `.github/workflows/probe.yml` | the step could never fail the job |
| suite/corpus/expected versions hardcoded to `v1.0.0`, output path fixed | `probes/run_probes.py` | v1.1.0 evidence was not reproducible by the committed runner; versioning had been solved by forking the suite directory |
| both claims pointed at evidence paths that do not exist | `convergence-claims/*.md` | evidence refs dangled |
| 11 near-identical probe scripts | `probes/*/` , `probes_v1_1/` | a new probe cost a code copy |
| `ys f` vs `ys -p f` inconsistency | `BUG01_probe.py` vs `P11_range_probe.py` | a wrong invocation compares the wrong output, silently |
| `datetime.utcnow()` deprecation | `probes/run_probes.py` | warning on every run |

### Retraction: this section's fix was still not a working gate

**2026-10-17.** The row above, "`ys` never installed in CI", was recorded as
fixed — and the fix installed the wrong artifact. `pip install yamlscript`
installs `libys` plus a Python binding and declares **no entry points**, so it
puts no `ys` on `PATH`, and the runner image (ubuntu-24.04) has no `ys` either.
On a fresh runner the suite would have failed at `ys is not on PATH` and exited
2: the job red for the wrong reason, `claim_state` SUSPECT, and no evidence. The
install step now downloads the `ys-<version>-linux-x64` release asset, which is
the binary the probes actually shell out to.

Verified by running the documented install in a clean venv and then in a fresh
clone: with `pip install yamlscript==0.2.8` the suite exits 2 and tells you to
run the command you had just run; with the release asset on `PATH` it exits 0.
No evidence file in this repository's history was produced by CI — every commit
touching `convergence-claims/evidence/` is by `whitecell-dev`, never by
`github-actions[bot]` — so no committed evidence ever depended on the broken
install. What remains unverified is the workflow itself: no successful run has
been observed, only that its inputs are now correct.

### What changed

- **`probes/manifest.json` is now the single source of truth.** Suite,
  corpus and expected versions, the pinned `ys` version, and every probe's
  corpus path, expected path, and invocation mode are declared as data. Adding
  a probe is a manifest edit plus two files.
- **One runner.** `probes/run_probes.py` executes every declared probe,
  distinguishes `run` (`ys FILE`) from `print` (`ys -p FILE`), supports both
  exact and substring expectation shapes, writes one evidence file per suite,
  and exits non-zero unless everything passes. The 11 duplicated probe scripts
  were deleted; `git log` retains them.
- **CI gates.** The pinned `ys` CLI from its GitHub release asset — the PyPI
  `yamlscript` package installs `libys` plus a Python binding and no `ys` — plus
  the runner's own exit code captured via `PIPESTATUS` under `bash -e`,
  `claim_state` exposed as a job output, and a final step that fails the job when
  the claim is SUSPECT. Artifact upload runs first, unconditionally.
- **`scripts/mutation_check.py`** reinstates a fixed defect on a copy of the
  transpiler in a temp directory and asserts the suite was green, then red. CI
  runs it, so a green suite is falsifiable rather than merely observed. Two
  mutations: the inclusive `(a .. b)` range form, which turns `range_2arg`, `range_nested` and
  `range_workflow` red; and `mod` reverting to `%`, which turns `mod_negative`
  red.
- **Status reclassification, deliberate.** `TR01_workflow` now reports ERROR
  where it previously reported FAIL. Same verdict, same non-zero exit, but the
  old runner discarded YS's stderr and so recorded an output mismatch instead
  of the real cause: `let requires an even number of forms in binding vector`.
  Every other probe's status is unchanged.
- **Knowledge layer.** `compound-packs/yamlscript-semantics/` holds eight
  prescriptive equivalence rules (validated: 8 discovered, 0 skipped) plus
  `resources/form-mapping.md` as storage, so planning grounds in them and review
  cites them. `CODING_STANDARDS.md` records the rules this repo has broken.

### Transpiler defects found while hardening

Both reproduce, and both are covered by a pack rule. **Both are now fixed**
(2026-10-17); item 2 records what the fix actually was, because the diagnosis
below it was wrong.

1. **FIXED — `mod` mapped to `%`.** `RENAMES` (`clj-to-ys.py:311`) and `OP_MAP` (`:353`) both mapped `mod`
   and `rem` to `%`, so `(mod -7 3)` transpiled to `-7 % 3`, evaluating to `-1`
   where Clojure gives `2`. YS `%%` is the floored form. `spec.md` already
   recorded the correct mapping, so the maps were the defect. It was invisible
   to every probe because they used positive operands, where `mod` and `rem`
   agree. Fixed in both maps; probe `mod_negative` (suite v1.2.0) pins it with
   a negative dividend and mutation `mod-reverts-to-remainder` proves it.
2. **FIXED — `let` in value position emitted two invalid YS forms.**
   `clj-to-ys.py:832-856` rendered `(let [k v] body)` inline as
   `(let [k=v] ...)` when it appeared inside a call argument, which YS rejects:
   `[k=v]` is one form and `let` wants name/value pairs. That is what failed
   `TR01_workflow`.

   **The diagnosis this file carried was wrong**, and the correction matters
   more than the fix. It said a correct fix "is not contained: YS has no inline
   `let`, so the binding must be hoisted into a preceding statement, which means
   separating statement position from expression position in the emitter", and
   the emitter's own KNOWN marker said YS "rejects inline `let` in value
   position". Executing `ys` instead of reasoning about it (`docs/clojure-vs-ys-gotchas.md`,
   verified on 0.2.8 and 0.3.5) showed that YS accepts `let` in value position
   happily — inside `fn` bodies, with multiple body forms — and rejects only the
   *binding shape*. The fix was one line: `[k v]`.

   Chasing it surfaced a second, worse defect in the same branch, one that had
   never been visible because the first one stopped execution: an unparenthesized
   infix body is evaluated as its **last operand**. `(let [n 3] n + 1)` is `1`,
   not `4`, on both releases — a plausible wrong number with no error at all.
   Parenthesizing an infix body fixes it; a bare `(n)` must not be wrapped,
   because that would be a call of `n`. The two lines are pinned separately by
   mutations `let-binding-form-reverts-to-clojure` and
   `let-infix-body-unwrapped`, plus probe `let_value_pos` (v1.3.0).

   Both `let` probes that had been carried as `xfail` XPASSED on the day of the
   fix and had to be deleted, which is what the xfail machinery is for.

### Coverage gaps still open

`REPORT.md` section 8 listed unenumerated compositions. Additionally
`probes/corpus/TR01.clj` and `probes/expected/TR01.json` exist but no probe
references them — they are the ancestor of `test_queries/find_dependents.clj`,
retained as research material rather than dead code. So is
`probes/corpus/TR01_simple.clj`, which was the richer variant of the same
`let` defect, carried for a while as the `xfail` fixture `TR01_simple_let`. It
was deleted on 2026-10-17: once the emitter was fixed it duplicated
`TR01_workflow`'s now-passing body exactly, so it held no information, and the
independent minimal witness for the same path is probe `let_value_pos`.
`convergence-claims/evidence_archive/run-v1.1.0.json` is
superseded by the canonical `convergence-claims/evidence/run-v1.1.0.json`; it
is archived under its own name so no second file answers to `run-v1.1.0.json`.
`probes_v1_1/` retains its frozen corpus and expected files in place, referenced
by the manifest, as do the newer `probes_v1_2/` and `probes_v1_3/`.

One gap this section did not list, found on 2026-10-17 while writing the map
probe: `(:a m)` — keyword as a function — is not implemented, and emits `:a(m)`,
which YS cannot resolve. `(get m :a)` works and emits `m.a`. Nothing probes the
broken form, because a permanently-failing probe is not a regression signal and
the repo has no `xfail` entry to put it in.
