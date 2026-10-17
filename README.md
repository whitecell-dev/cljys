# cljys

cljys is a Clojure→YAMLScript transpiler (`clj-to-ys.py`, a single 1090-line
Python file) surrounded by the apparatus that watches it: a versioned probe
suite, convergence claims that expire when the suite goes red, machine-written
evidence files, and a mutation check that reintroduces a known defect to prove
the green is falsifiable. The transpiler runs. The interesting part of this repo
is what happens when it stops running correctly. This is a research artifact and
a system under observation — not a library, not a product, not published or
versioned for consumption. Nothing here is importable (`clj-to-ys.py` cannot be
imported; see below), and the only entry point is a CLI.

## Read This First: Three Things That Will Bite You

**The transpiler cannot be imported, and its own docstring gives it the wrong
name.** The file is `clj-to-ys.py`; the hyphen means `import clj_to_ys` fails
with a `SyntaxError`, so no test, no other module, and no REPL can reach
`tokenize`, `parse`, or `Transpiler`. Every consumer in this repo shells out
instead — `probes/run_probes.py:51` invokes it as a subprocess. The hazard is
that the file documents itself under the name people will try:
`clj-to-ys.py:3` says `clj_to_ys.py — Tiny Clojure → YAMLScript transpiler` and
the usage block at `clj-to-ys.py:11-13` repeats it. This exact error shipped in
the previous README, which is why `CODING_STANDARDS.md:51-52` exists as a rule
("A command in the README must run… Check the filename against the tree before
publishing").

**Every probe run rewrites tracked files, and the mutation check does it three
times.** `convergence-claims/evidence/run-<version>.json` is generated output,
written unconditionally at `probes/run_probes.py:145-147` on every suite run —
including the timestamp field, so the content churns even when no verdict
changes. `scripts/mutation_check.py:74-104` runs the suite three times per
mutation (baseline, mutated, restored), so one invocation of that script leaves
three timestamps rewritten in your working tree. This is intentional and
documented at `CODING_STANDARDS.md:43-44` ("Evidence is generated, not authored.
Never hand-edit"), and `.gitignore:59-63` explains why these files are tracked
rather than ignored. But it means `git status` is dirty after any local probe
run, and a diff of an evidence file is almost always timestamp noise rather than
a behavior change.

**`REPORT.md` is hand-written, carries no staleness banner, and contradicts the
evidence files it cites.** `REPORT.md` records the v1.0.0 run as "5 PASS, 5
FAIL, 0 ERROR" while the committed file it names,
`convergence-claims/evidence/run-v1.0.0.json`, records 9 PASS and 1 ERROR. The
convergence claim repeats the same stale figures. *Both files now carry a
staleness banner and a corrections section*, and the stale counts are marked as
historical rather than restated as current — a new run cannot retroactively
validate the 2026-10-05 run those figures describe. Treat
`convergence-claims/evidence/*.json` as the record and `REPORT.md` as a
narrative that was true when written and is checked by nobody.

## Running Things

Dependencies are `python3` (3.12 here) and `ys`, the YAMLScript CLI. `ys` is not
vendored — `.cljys/` is gitignored (`.gitignore:22`), so a fresh clone has
neither the venv nor the binary, and every probe is unverifiable without it.

```bash
pip install yamlscript==0.2.8     # version pinned in probes/manifest.json:3
```

`probes/run_probes.py:155-159` exits 2 with an install hint if `ys` is absent,
and `:160-164` prints a warning — not an error — if the installed version
differs from the pin, so a local run on a different `ys` will produce evidence
that is not comparable to CI's. Point that output at CI, not at the claim.

Transpile one file:

```bash
python3 clj-to-ys.py input.clj              # YS to stdout
python3 clj-to-ys.py input.clj -o out.ys    # or to a file
```

CLI surface is `input` (a path, or `-` for stdin) and `-o/--output`, both at
`clj-to-ys.py:1069-1071`. There is no `--version`, no `--check`, and no
exit-code-on-warning behavior; the process exits 0 on a successful transpile
regardless of whether the emitted YS is valid.

Run the probes:

```bash
python3 probes/run_probes.py                  # all suites, 17 probes
python3 probes/run_probes.py --suite v1.2.0   # one suite, 2 probes
```

Three suites now exist: v1.0.0 (10 probes), v1.1.0 (5, the range fix), and
v1.2.0 (2, `mod` with a negative dividend and the `_binding_coll` emitter
branch). Exit code is non-zero unless every probe in every selected suite passes
(`probes/run_probes.py:189`), which is what CI gates on. Adding a probe is a
manifest edit plus two files — never a new script (`CODING_STANDARDS.md:12-14`);
the eleven near-identical `*_probe.py` scripts this repo used to have were
deleted for that reason.

```bash
python3 scripts/mutation_check.py   # proves the suite can fail
```

Caveat, stated in its own docstring at `scripts/mutation_check.py:12-13`: this
edits a tracked file in place and restores it from its own in-memory copy, not
from git. Run it on a disposable checkout. It holds two mutations
(`range-end-becomes-inclusive`, `mod-reverts-to-remainder`).

```bash
./run_tests.sh                      # transpiles test_suite/*.clj into results/
```

This is the only aggregate runner over `test_suite/`, and it is not a CI gate:
CI runs only the probes and the mutation check. It transpiles each case, runs
`ys FILE` on the output (executing it, which catches invalid output and runtime
failures alike), and **now exits non-zero if any case fails** — it previously
exited with the status of its last command, always 0, which meant the 14-pass /
1-fail result it printed was not enforced anywhere. That one failure,
`014_maps`, is real and still open. Output lands in `results/`, which is
gitignored twice (`.gitignore:58`, `.gitignore:64`), so its artifacts are
unreviewable by construction.

```bash
python3 generate_tests.py           # regenerates test_suite/*.clj (15 files)
```

Writes to `test_suite/` unconditionally (`generate_tests.py:69-74`) and
overwrites tracked files. Verified by diffing all 15 generated bodies against
the tracked copies: byte-identical as of this commit. Two of the generated cases
(`006_loops_each.clj`, `007_loops_nested.clj`) are written in YAMLScript `each`
syntax, not Clojure `doseq`, so they exercise the pass-through path at
`clj-to-ys.py:442` rather than the mapping.

```bash
python3 scripts/vendor_ce_skills.py           # regenerate .opencode/skills/
python3 scripts/vendor_ce_skills.py --check   # non-zero if it drifted
```

Agent-tooling only; unrelated to the transpiler. Its docstring
(`scripts/vendor_ce_skills.py:13`) and the gitignored `.ce/README.md` both name
the generator `.ce/vendor-skills.py`, which does not exist — the real path is
the one above.

There is no lint command, no formatter config, no type checker, and no
`Makefile`, `pyproject.toml`, or `requirements.txt` in the tree. CI runs exactly
two things: the probe suite and the mutation check
(`.github/workflows/probe.yml:32-48`).

No environment variables are read. Grepping `os.environ` and `getenv` across
the repo's own Python finds nothing; the transpiler imports only `re`, `sys`,
`argparse`, and `typing` (`clj-to-ys.py:16-19`), which is also the evidence for
the determinism claim below.

## Container

Not applicable. There is no Dockerfile, compose file, Procfile, or IaC in the
tree; the whole pipeline is `python3` plus the `ys` binary on `PATH`, which is
what `.github/workflows/probe.yml:22-30` installs.

## Verified Working

- The probe runner's exit code reflects probe verdicts, not just whether it ran
  — `probes/run_probes.py:189`.
- CI installs the pinned `ys` and reads the runner's status through `PIPESTATUS`
  rather than `$?` after a pipe, then fails the job on non-zero —
  `.github/workflows/probe.yml:26-30`, `:39-43`, `:72-77`.
- The `range` mapping is falsifiable: reverting it to the inclusive YS form
  turns the v1.1.0 suite red, and restoring turns it green —
  `scripts/mutation_check.py:26-39`, `:82-104`.
- The `mod` mapping is falsifiable: reverting `OP_MAP` to `%` turns
  `mod_negative` red, and restoring turns it green —
  `scripts/mutation_check.py`, mutation `mod-reverts-to-remainder`.
- 14 of the 17 probes compare exact stdout rather than a substring, decided by
  the expected file's own shape (`probes/run_probes.py:77-97`); the suites'
  current verdicts are 9 PASS / 1 ERROR, 5 PASS / 0 ERROR, and 2 PASS /
  0 ERROR, recorded in `convergence-claims/evidence/run-v1.0.0.json`,
  `run-v1.1.0.json`, and `run-v1.2.0.json`.
- The pack is loaded, not aspirational: eight rule files are present and
  referenced by `.compound-engineering/config.yaml:18-19`, listed at
  `compound-packs/yamlscript-semantics/README.md:18-27`. Verified by inspection.
- `generate_tests.py` reproduces `test_suite/` byte-identically. Verified by
  diffing all 15 generated bodies against the tracked files.

## Known to Break

| Breakage | Status | Evidence |
|---|---|---|
| `let` in value position emits `(let [k=v] …)`, which YS rejects | KNOWN, not fixed | `clj-to-ys.py:825-842`, KNOWN marker inline at `:827` |
| `TR01_workflow`, the only full query shape probed, fails on that defect | ENFORCED (as a failure) | `convergence-claims/evidence/run-v1.0.0.json`, probe `TR01_workflow`: `ys failed: Error: let requires an even number of forms in binding vector` |
| `probes/corpus/TR01_simple.clj` — the *unreferenced* variant of the wired `TR01_simple` probe — fails at runtime with that same `let` defect, while the wired 4-line version drops the construct and passes | KNOWN, not fixed | `probes/corpus/TR01_simple.clj` transpiles cleanly, then `Error: let requires an even number of forms in binding vector`; contrast `probes/workflows/TR01_simple.clj` |
| CI can never be green: that ERROR makes the runner exit 1, which fails the job | ENFORCED | `probes/run_probes.py:189` + `.github/workflows/probe.yml:72-77` |
| The convergence claim therefore stays SUSPECT | KNOWN | `convergence-claims/cljys-calyx-query.md` § Status |
| `RENAMES["mod"]` is shadowed for the infix path, so no probe constrains it | UNTESTED | KNOWN marker inline at `clj-to-ys.py:307-310`; verified by mutating that entry alone and observing the suite stay green. Reachable via `(apply mod …)` |
| Nothing consumes the claim state, so "downstream workers stop" is untested | UNTESTED | `.github/workflows/probe.yml:13-14` exposes `claim_state`; no in-repo consumer |
| `REPORT.md` and the claim both record a probe run that is not the committed one | LABELED, historical | Banner at `REPORT.md` top + §3 note + "Corrections to this file" in the claim; stale counts marked historical rather than restated, since a new run cannot retroactively validate the 2026-10-05 run |
| `REPORT.md` §10 called that same run "9 PASS, 1 FAIL"; the committed file says ERROR | FIXED | Now reads ERROR, matching `convergence-claims/evidence/run-v1.0.0.json` |
| Claim evidence refs pointed at `probes/compositions/`, a directory that does not exist | FIXED | `convergence-claims/cljys-calyx-query.md` § Evidence References now names `probes/corpus/`; correction recorded in its new corrections section |
| `REPORT.md` claimed the CHALLENGE path was tested and "PASSED" | FIXED (retracted in place) | `REPORT.md` §6 now reads "NOT RUN — no such test exists", with the original text retained as a record; §5 and §9 corrected to match |
| `probes/corpus/TR01.clj` and `probes/expected/TR01.json` are read by nothing | KNOWN, retained deliberately | No `manifest.json` entry. `TR01.clj` is the ancestor of `test_queries/find_dependents.clj` — research material, not dead code. Classified at `REPORT.md` § "Coverage gaps still open" |
| `probes/corpus/TR01_simple.clj` is an unreferenced, divergent duplicate of `probes/workflows/TR01_simple.clj` | KNOWN, retained deliberately | Not a duplicate: it is the richer variant that still exercises the failing construct. See the `let` rows above |
| `range_workflow` asserts one substring (`"count=4"`) and would pass on almost any wrong output | UNTESTED | `probes_v1_1/expected/range_workflow.json`; comparison shape at `probes/run_probes.py:79-83`. Frozen suite — fixing it needs a new version |
| `TR01_simple` and `TR01_workflow` assert substrings, not exact output | UNTESTED | `probes/expected/TR01_simple.json`, `TR01_workflow.json`. Frozen v1.0.0 suite |
| **Two different files are both named `run-v1.1.0.json`** | KNOWN, keep them distinct | `convergence-claims/evidence/run-v1.1.0.json` is canonical; `convergence-claims/evidence_v1_1/run-v1.1.0.json` is superseded, in an older schema, and reports `range_nested` PASS on output containing four extra `(nil nil nil nil)` lines. Do not cite the `_v1_1` copy |
| The previous README claimed an LLM normalization front-end | FALSE | No prompt, model config, or network call exists in the tree; `clj-to-ys.py:16-19` |
| The previous README claimed `ys -c` produces a native binary | FALSE | `ys --help`: `-c, --compile  Compile YS to Clojure`; native binary is `-b, --binary`. No GraalVM in this repo |
| `run_tests.sh` could not fail a build | FIXED | It now exits non-zero when any case fails. Verified: it reports 14 passed / 1 failed and exits 1. `014_maps` is a real, still-open failure |
| The pack path was wrong in two docs (`.ce/packs/…`, real path `compound-packs/…`) | FIXED | `REPORT.md` §11 and `CODING_STANDARDS.md:17` now name `compound-packs/`, matching `.compound-engineering/config.yaml:19` |
| `.compound-engineering/config.yaml` declares `docs_root: docs`, which does not exist | KNOWN, documented | The comment now says it declares a location for CE to write into, not a directory that is currently there |

## Repository Structure

```
cljys/
├── clj-to-ys.py              The transpiler. Not importable; CLI only. The system under observation.
├── probes/                   Probe suite. manifest.json is the single source of truth; run_probes.py is the one runner.
├── probes_v1_1/              Frozen v1.1.0 corpus + expected, in a second directory so v1.0.0 stays byte-identical.
├── probes_v1_2/              Same convention for v1.2.0 (mod with a negative dividend, _binding_coll).
├── convergence-claims/       Hand-written claims (expire when the suite goes red) + generated evidence/*.json.
├── compound-packs/           The knowledge layer: 8 hand-written YS↔Clojure equivalence rules. Live; config points here.
├── scripts/                  mutation_check.py (proves the suite can fail), vendor_ce_skills.py (agent tooling).
├── .github/workflows/        probe.yml. The only CI. Runs probes + mutation check, fails the job on red.
├── test_suite/               Generated corpus (generate_tests.py). 15 files. Not used by probes.
├── test_primitives/          Hand-written Clojure exercises. No runner references these.
├── test_queries/             Realistic query shapes. Not referenced by any runner; probes/corpus/TR01.clj is their ancestor.
├── spec.md                   YAMLScript knowledge base. Canonical for mappings — where it and the code disagree, it is right.
├── CODING_STANDARDS.md       13 rules, each one this repo has broken or could break invisibly.
├── REPORT.md                 Hand-written research report. Carries a staleness banner; §6 is a retraction, not a result.
├── calyx_mcp_v6.json         444 KB tracked JSON fixture. Two probes actually read it at runtime.
├── AGENTS.md                 Agent operating mode for this repo.
├── LICENSE                   MIT.
├── run_tests.sh              Only aggregate runner over test_suite/. Always exits 0.
├── generate_tests.py         Regenerates test_suite/.
├── .compound-engineering/    config.yaml; points at the pack above. docs_root: docs, which does not exist.
├── .ce/                      GITIGNORED vendored third-party checkout. Its README documents paths that don't exist. Not project code.
├── .cljys/                   GITIGNORED local venv. Not on PATH; `ys` is installed globally instead.
├── .opencode/skills/         Generated from .ce/ by scripts/vendor_ce_skills.py. Do not hand-edit.
├── results/                  GITIGNORED run_tests.sh output. Mixed-vintage: 001_*.ys is newer than the rest; 014_maps.error is a stale empty file.
├── test.clj / test.ys / debug.ys   GITIGNORED scratch from manual poking.
└── __pycache__/              GITIGNORED.
```

## Safety Claims vs Ground Truth

| Claim | Status | Evidence |
|---|---|---|
| An LLM front-end normalizes Clojure into a canonical subset before the emitter | FALSE | Nothing in the tree implements it; `clj-to-ys.py:16-19` |
| The canonical-subset rules "are handled automatically by the LLM front-end prompt" | FALSE | No prompt artifact exists; the rules are prose in `spec.md:244-291` |
| `ys -c` compiles to a standalone native binary via GraalVM | FALSE | `ys --help` (`-c` compiles to Clojure; `-b` is binary); no GraalVM here |
| The emitter is deterministic | ENFORCED | `clj-to-ys.py:16-19`: `re`, `sys`, `argparse`, `typing` only; no clock, RNG, or network |
| The probe suite is "independently verifiable; probes never assume cljys correctness" | PARTIAL | True of expectations (`probes/expected/*.json` are hand-written), but `TR01_simple`, `TR01_workflow`, and `range_workflow` assert substrings (`probes/run_probes.py:79-83`) and the two TR01 probes read a 444 KB fixture from the repo root (`probes/manifest.json:85-95`, cwd pinned at `probes/run_probes.py:70`) |
| When probes fail the claim becomes SUSPECT and downstream workers stop | PARTIAL | The transition is real and mechanical (`.github/workflows/probe.yml:50-59`, `:72-77`); no worker exists to stop, so the second half is untested. `REPORT.md` §5, §6 |
| The CHALLENGE path was tested and passed | RETRACTED | `REPORT.md` §6 now records it as never run; no test file implements it. Steps 1 and 3 map to real CI logic, steps 2 and 4 have no implementation here |
| Claim evidence refs point at existing paths | TRUE | Fixed: the v1.0.0 claim named `probes/compositions/`, which does not exist; it now names `probes/corpus/`, verified against the tree. The v1.1.0 claim was already correct |
| A green suite is falsifiable | PARTIAL | `scripts/mutation_check.py` proves it for two mutations. Still uncovered: the inclusive-range emission at `clj-to-ys.py:613` is now probed by `binding_coll` but has no mutation, and no mutation covers `RENAMES` |
| Corpus and expected files are frozen and versioned | MOSTLY | Frozen for the suites (`CODING_STANDARDS.md:19-22`), but `convergence-claims/evidence_v1_1/` is a superseded twin in an older schema, and v1.1.0's corpus lives in a forked directory (`probes/manifest.json:16-18`) |
| Version pinning is in one place | ENFORCED | `probes/manifest.json:3`, read by `probes/run_probes.py:158` and `.github/workflows/probe.yml:27` |
| The `ys` version is enforced, not just recorded | PARTIAL | Mismatch warns and continues (`probes/run_probes.py:160-164`); a local run on a different version writes evidence the claim still cites |
| The CI gate executes | ENFORCED | `.github/workflows/probe.yml:32-43` uses `PIPESTATUS`; the five gate defects listed in `REPORT.md` §11 are fixed |
| `mod` maps to YS `%%` | TRUE | `RENAMES` and `OP_MAP` both map it to `%%` (`clj-to-ys.py:311`, `:353`), matching `spec.md:141`. Pinned by `mod_negative` and proven by the `mod-reverts-to-remainder` mutation. The `RENAMES` entry specifically remains unprobed — see § "Known to Break" |
| The pack contains 8 rules, 0 skipped | ENFORCED | Eight rule files present; `compound-packs/yamlscript-semantics/README.md:18-27` |
| The pack is consulted by tooling | PARTIAL | `.compound-engineering/config.yaml:18-19` wires it for CE skills; the transpiler itself never reads it |
| Every emitter branch has a probe | UNVERIFIED | `CODING_STANDARDS.md:6-11` states the rule; 17 probes over 1090 lines, and `REPORT.md` §8 lists unenumerated compositions |
| Agent tooling is reproducible from the vendored source | PARTIAL | `--check` passes in a checkout that has `.ce/` (verified: "15 vendored skills match source"), but `.ce/` is gitignored (`.gitignore:75`), so from a fresh clone the source is absent, the script cannot run, and the committed `.opencode/skills/` cannot be regenerated |

## Current Risks (Ranked by Likelihood)

1. ✅ ~~`mod` silently produces a wrong sign on negative operands~~ — **fixed**.
   Both maps now emit `%%`; `mod_negative` pins it with a negative dividend and
   mutation `mod-reverts-to-remainder` proves the probe catches a regression.
   `RENAMES`'s entry is still unprobed.
2. ❗ CI is red on every push to `main`/`master` and always will be until
   `TR01_workflow` passes (`.github/workflows/probe.yml:72-77`).
3. ❗ `let` in value position blocks the only realistic query shape the suite
   exercises (`clj-to-ys.py:825-842`; `probes/workflows/TR01_workflow.clj`).
   The fix is not contained — it needs statement/expression separation in the
   emitter, and it would retire this repo's headline failure.
4. ❓ No lint, no type checking, no CI job beyond probes — an emitter change
   that compiles and produces wrong output is caught only if someone remembers
   to add a manifest entry (`.github/workflows/probe.yml:32-48`).
5. ❗ The evidence files cited by both convergence claims churn on every run, so
   "the cited run" is whatever ran last (`.gitignore:59-63`). Two files are
   named `run-v1.1.0.json`; only the one under `evidence/` is canonical.
6. ❓ `REPORT.md` and the claim prose are hand-maintained with no generator and
   no reviewer, so they drift silently. Both now carry staleness banners, which
   slows the drift but does not stop it.
7. ❗ 17 probes cover a fraction of the emitter's forms; the enumeration itself is
   incomplete (`REPORT.md` §8).
8. ✅ The decorative-CI gate was real and is fixed: five separate defects that
   meant the suite had never run in CI and could never fail a job
   (`REPORT.md` §11, fixed at `.github/workflows/probe.yml:26-77`).
9. ✅ The `range` end-semantics bug is fixed, probed, and mutation-proven
   (`REPORT.md` §10, `probes_v1_1/`, `scripts/mutation_check.py`).
10. ❓ Eleven duplicated probe scripts were replaced by a manifest
    (`CODING_STANDARDS.md:12-14`), but orphan corpus files remain. They are now
    classified rather than merely noted: `probes/corpus/TR01.clj` is an
    ancestor of `test_queries/`, and `probes/corpus/TR01_simple.clj` still
    reproduces the `let` defect that the wired probe was simplified to avoid.

## Contribution Guidelines (Failure-First)

Prioritized:

- A reproducible breakage: corpus file, expected file, `manifest.json` entry,
  and the diff that shows the wrong output (`CODING_STANDARDS.md:6-11`).
- A mutation that proves a fix causal, not a claim that it works
  (`scripts/mutation_check.py:26-39`).
- Raw evidence. Probes run the real `ys`; asserting on emitted text is not
  evidence (`CODING_STANDARDS.md:23-24`).
- A new pack rule before a new form family, not after
  (`CODING_STANDARDS.md:15-18`).
- Fixing a wrong `expected/*.json` by adding a suite version rather than editing
  the old one (`CODING_STANDARDS.md:19-22`).

Deprioritized:

- Features and emitter branches with no probe attached.
- "Intuitive" Clojure↔YS mappings — settle them with `ys -p -e '<expr>'` in a
  second (`CODING_STANDARDS.md:28-30`).
- Refactors of `clj-to-ys.py` that leave the probe suite unchanged.
- Edits to `REPORT.md` or the claim prose that are not backed by a fresh
  `run_probes.py` output.
- Anything that pushes, publishes, or creates branches; the vendored skill set
  excludes those tools for that reason (`scripts/vendor_ce_skills.py:25-35`).

## This Is a Survival Lab

The transpiler is the specimen; the repo is built to break it cleanly, record
how it broke, take pressure from outside, and notice when its own meaning
drifts.

- **Break cleanly.** Every probe verdict lands as machine-written JSON with the
  input, the expected output, the actual output, and a diff
  (`probes/run_probes.py:100-134`), so a failure is a data record, not a
  transcript someone has to reconstruct.
- **Record its own errors.** A probe that produces invalid YS is recorded as
  ERROR with `ys`'s stderr, not as an output mismatch
  (`probes/run_probes.py:122-125`); `TR01_workflow` carries the real cause
  because of this.
- **Invite outside pressure.** A claim is scoped, conditional, and cites a
  specific run; it expires when the suite regresses rather than requiring
  someone to notice (`convergence-claims/cljys-calyx-query.md:7-13`).
- **Track semantic drift.** Clojure and YS share enough syntax that code
  compiling in both can mean different things; each known divergence is a
  frozen, versioned rule plus a probe (`compound-packs/yamlscript-semantics/README.md:18-27`).
- **Prove its own green is falsifiable.** One mutation reintroduces a fixed
  defect and asserts red-then-green, in CI, so "everything passes" is a result
  rather than an absence of information (`scripts/mutation_check.py`,
  `.github/workflows/probe.yml:45-48`).

It does not guarantee correct transpilation. Fifteen probes and one mutation
against a 1090-line emitter is a floor, not a proof.

## Notes on the Reports

Generated artifacts, all produced by `python3 probes/run_probes.py`:

- `convergence-claims/evidence/run-<version>.json` — one file per suite.
  Contains `timestamp`, per-probe `input`, `expected_output`, `actual_output`,
  `diff`, `status`, and `suite` (`probes/run_probes.py:137-148`). Regenerating
  them is the only correct way to change them; they are tracked on purpose
  (`.gitignore:59-63`) and their `timestamp` fields differ on every run, so
  never hand-edit one to make a claim line up (`CODING_STANDARDS.md:43-44`).
- `convergence-claims/evidence_v1_1/run-v1.1.0.json` — **a second file with the
  same name as the canonical one**, superseded by
  `convergence-claims/evidence/run-v1.1.0.json` (`REPORT.md`, § "Coverage
  gaps still open"). It uses an older record schema (no `input`, `kind`, or
  `passed` fields), and its `range_nested` entry reports PASS on an
  `actual_output` containing four extra `(nil nil nil nil)` lines. Both files
  are retained: the `_v1_1` copy is the record of the older run, not a second
  source of truth. **Do not cite it.** Neither file was hand-edited to
  reconcile them.
- Hand-written, not generated by anything: `REPORT.md`,
  `convergence-claims/*.md`. Their `- current state:`, `- latest probe run:`,
  and `- probe summary:` fields are placeholders no script ever rewrites, which
  is how `convergence-claims/cljys-calyx-query.md:31` came to disagree with the
  evidence file it names three lines above.
- `results/*.ys` — `run_tests.sh` output. Gitignored, unreviewable, and mixed
  vintage: `results/001_basic_assignment.ys` is newer than the rest of the
  directory, and `results/014_maps.error` is a zero-byte leftover the runner only
  deletes on a pass (`run_tests.sh:39`).