# cljys

A Clojure → YAMLScript transpiler, and the apparatus that watches it: a versioned probe suite, machine-written evidence, convergence claims that expire when the suite goes red, and a mutation check that reintroduces a known defect to prove the green is falsifiable. A research artifact, not a library: nothing here is importable, and the CLI is the only entry point. The interesting part of this repo is what happens when the transpiler stops running correctly.

```bash
# `ys` is a release asset, not a pip package (the pin: probes/manifest.json:3)
YS_VERSION=0.2.8
curl -fsSL https://github.com/yaml/yamlscript/releases/download/$YS_VERSION/ys-$YS_VERSION-linux-x64.tar.xz | tar -xJ
export PATH="$PWD/ys-$YS_VERSION-linux-x64:$PATH"

make probe                  # every probe suite; CI gates on this
python3 clj-to-ys.py q.clj  # transpile one file to stdout
```

**Status: green, with nothing marked `xfail`.** Known limitations live in `KNOWN_ISSUES.md`. 23 probes in 5 suites and 6 mutations (`make counts` prints both), plus 15 aggregate cases via `make test` — all pass, all execute real `ys`. The last two defects were fixed on 2026-10-17: `let` in value position (a binding form YS rejects, plus a body it silently mis-evaluates) and map-literal keys, which is what `014_maps` was. CI gates on all four commands (`probe`, `mutate`, `test`, `check`). Everything below is either how to run it, or what is still broken.

## Read This First: Three Things That Will Bite You

**The transpiler cannot be imported.** The file is `clj-to-ys.py`; the hyphen means `import clj_to_ys` fails with a `SyntaxError`, so no test, no other module, and no REPL can reach `tokenize`, `parse`, or `Transpiler`. Every consumer in this repo shells out instead — `probes/run_probes.py` invokes it as a subprocess. The hazard was worse than that until recently: the file documented itself under the name people will try, saying `clj_to_ys.py — Tiny Clojure → YAMLScript transpiler` at `clj-to-ys.py:3` and repeating it in the usage block at `:11-13`, so the error you would have hit from the shell was the one the docstring handed you. Both now name the real file. This exact error shipped in the previous README, which is why `CODING_STANDARDS.md:51-52` exists as a rule ("A command in the README must run… Check the filename against the tree before publishing"). The name is still wrong for a module; only the documentation now matches the tree.

**A probe run rewrote tracked files, and the mutation check did it three times per mutation.** `convergence-claims/evidence/run-<version>.json` was written unconditionally, timestamp included, so every run left `git status` dirty with noise rather than a behavior change, and `scripts/mutation_check.py` ran the suite three times per mutation against the tracked transpiler, which is why its docstring told you to use a disposable checkout. Both are fixed: the runner now rewrites an evidence file only when something other than the timestamp changed (`probes/run_probes.py`), and the mutation check applies each mutation to a copy in a temp directory and runs with `--no-evidence` (`scripts/mutation_check.py:92-127`), so it is safe in a working checkout. Evidence is still tracked on purpose (`.gitignore:65-70`, `CODING_STANDARDS.md:43-44`): it is generated, never hand-edited, and now only churns when a verdict or an output actually moved.

**`REPORT.md` is hand-written, carries no staleness banner, and contradicts the evidence files it cites.** `REPORT.md` records the v1.0.0 run as "5 PASS, 5 FAIL, 0 ERROR" while the committed file it names, `convergence-claims/evidence/run-v1.0.0.json`, recorded 9 PASS and 1 ERROR. The convergence claim repeats the same stale figures. *Both files now carry a staleness banner and a corrections section*, and the stale counts are marked as historical rather than restated as current — a new run cannot retroactively validate the 2026-10-05 run those figures describe. Treat `convergence-claims/evidence/*.json` as the record and `REPORT.md` as a narrative that was true when written and is checked by nobody.

## Running Things

Dependencies are `python3` (3.12 here) and `ys`, the YAMLScript CLI. `ys` is not vendored — `.cljys/` is gitignored (`.gitignore:22`), so a fresh clone has neither the venv nor the binary, and every probe is unverifiable without it.

```bash
# The `ys` CLI is a GitHub release asset, not a pip package: `pip install
# yamlscript` installs libys plus a Python binding and no `ys`. Version is the
# pin in probes/manifest.json:3, read here by hand and by CI from the manifest.
YS_VERSION=0.2.8
curl -fsSL https://github.com/yaml/yamlscript/releases/download/$YS_VERSION/ys-$YS_VERSION-linux-x64.tar.xz | tar -xJ
export PATH="$PWD/ys-$YS_VERSION-linux-x64:$PATH"
ys --version
```

**`pip install yamlscript` does not install `ys`.** The PyPI package ships `libys` plus a Python binding and declares no entry points, so a fresh environment that follows the old instruction ends up with no `ys` on `PATH` at all — verified: a fresh clone plus `pip install yamlscript==0.2.8` exits 2 with "install with: pip install yamlscript==0.2.8", the instruction that had just been carried out. The CLI is a GitHub release asset (`ys-<version>-linux-x64.tar.xz`), which is what the recipe above and CI both use. `.github/workflows/probe.yml:33-46` had the pip form, so the gate could not have executed on a fresh runner; the runner image has Java but no `ys`.

`probes/run_probes.py` exits 2 with an install hint if `ys` is absent, and refuses to run under `--strict` when the installed version is not the pin — a mismatch warns locally and fails in CI, because CI's evidence is the one the claims cite. A local run on a different `ys` still produces evidence that is not comparable. All of the above was re-verified on 0.3.5, the current release: the `range`, `mod`/`rem`, `let`, and map-literal behaviours this repo pins are unchanged, but error wording differs and YS maps print in a different key order, so exact-output probes written against 0.2.8 are version-fragile (see `docs/clojure-vs-ys-gotchas.md`).

Transpile one file:

```bash
python3 clj-to-ys.py input.clj              # YS to stdout
python3 clj-to-ys.py input.clj -o out.ys    # or to a file
```

CLI surface is `input` (a path, or `-` for stdin) and `-o/--output`, both at `clj-to-ys.py:1106-1107`. There is no `--version`, no `--check`, and no exit-code-on-warning behavior; the process exits 0 on a successful transpile regardless of whether the emitted YS is valid.

Run the probes:

```bash
make probe                                # python3 probes/run_probes.py
python3 probes/run_probes.py --suite v1.2.0   # one suite
```

Five suites exist: v1.0.0 (10 probes, the workflow shapes), v1.1.0 (5, the range fix), v1.2.0 (2, `mod` with a negative dividend and the `_binding_coll` emitter branch), v1.3.0 (3, `let` in value position and map-literal keys) and v1.4.0 (3, string quoting and multi-arg print). `make counts` prints those numbers from the manifest rather than trusting this paragraph. Exit code is non-zero unless every probe passes and no `xfail` probe unexpectedly passes (`probes/run_probes.py`), which is what CI gates on. Adding a probe is a manifest edit plus two files — never a new script (`CODING_STANDARDS.md:12-14`); the eleven near-identical `*_probe.py` scripts this repo used to have were deleted for that reason.

`"status": "xfail"` marks a probe that is *expected* to fail: it reports XFAIL while it does and XPASS once it stops, and XPASS is an error (`probes/run_probes.py`). Nothing carries it now. Both entries that did — the `let` binding form and the fixture that reproduced it — were retired the day their defect was fixed, which is the only way that flag stays honest rather than becoming a place to park regressions.

```bash
make mutate                               # python3 scripts/mutation_check.py
```

It holds six mutations (`range-end-becomes-inclusive`, `mod-reverts-to-remainder`, `let-binding-form-reverts-to-clojure`, `let-infix-body-unwrapped`, `map-keys-unquoted`, `string-quoting-reverts-to-double`), each applied to a temp copy of the transpiler, so nothing tracked is edited and no caveat about disposable checkouts applies. Every fix in the emitter has one; that is rule 9, and it is what makes "everything passes" a result rather than an absence of information.

```bash
make test                                 # ./run_tests.sh
```

The only aggregate runner over `test_suite/`, and a CI gate as of 2026-10-17. It transpiles each case, runs `ys FILE` on the output, and exits non-zero if any case fails: 15 executed, 0 failed. **It has no output oracle** — a case can emit wrong YS that still executes, so it is an execution smoke test, not a correctness test; exact output is checked by `make probe`. It ran with `continue-on-error` while `014_maps` was open; that case was a map-literal emission bug, now fixed and pinned by probes `map_kw` and `map_get`, so the step gates and the xfail list it needed is gone with it. Output lands in `results/`, which is gitignored twice (`.gitignore:64`, `.gitignore:70`), so its artifacts are unreviewable by construction — which is the argument for gating it rather than not.

```bash
make check                                # python3 scripts/check_input_boundary.py
```

Asserts that malformed Clojure is rejected with a typed code and exit 2, never
silently repaired into plausible YS. It covers the parser and the emitter's
binding/arity checks; unlisted arity errors still surface as a traceback.

```bash
python3 generate_tests.py           # regenerates test_suite/*.clj (15 files)
```

Writes to `test_suite/` unconditionally (`generate_tests.py:69-74`) and overwrites tracked files. Verified by diffing all 15 generated bodies against the tracked copies: byte-identical as of this commit. Two of the generated cases (`006_loops_each.clj`, `007_loops_nested.clj`) are written in YAMLScript `each` syntax, not Clojure `doseq`, so they exercise the pass-through path at `clj-to-ys.py:442` rather than the mapping.

```bash
python3 scripts/vendor_ce_skills.py           # regenerate .opencode/skills/
python3 scripts/vendor_ce_skills.py --check   # non-zero if it drifted
```

Agent-tooling only; unrelated to the transpiler. Its docstring named the generator `.ce/vendor-skills.py`, which does not exist; it now names the real path, `scripts/vendor_ce_skills.py` (`scripts/vendor_ce_skills.py:12-14`), and the gitignored `.ce/README.md` still names the old one.

There is no lint command, no formatter config, no type checker, and no `pyproject.toml` or `requirements.txt` in the tree. `Makefile` is the only build file, and it wraps the four commands above plus `clean` (gitignored output only). CI runs four steps, all gating: the probe suite with `--strict`, the mutation check, the input-boundary check, and `run_tests.sh` (`.github/workflows/probe.yml`).

No environment variables are read. Grepping `os.environ` and `getenv` across the repo's own Python finds nothing; the transpiler imports only `re`, `sys`, `argparse`, and `typing` (`clj-to-ys.py:16-19`), which is also the evidence for the determinism claim below.

## Container

Not applicable. There is no Dockerfile, compose file, Procfile, or IaC in the tree; the whole pipeline is `python3` plus the `ys` binary on `PATH`, which is what `.github/workflows/probe.yml:33-46` installs.

## Verified Working

- The probe runner's exit code reflects probe verdicts, not just whether it ran — `probes/run_probes.py`, where FAIL, ERROR, UNKNOWN and XPASS all count as bad.
- `xfail` is a real status, not a comment: a marked probe reports XFAIL while it fails and XPASS once it passes, and XPASS fails the run so the entry cannot outlive the defect (`probes/run_probes.py`). Verified by marking a passing probe `xfail` and observing exit 1, then by watching both real entries XPASS the day their defect was fixed.
- The workflow reads the runner's status through `PIPESTATUS` rather than `$?` after a pipe, then fails the job on non-zero — `.github/workflows/probe.yml:57-61`, `:86-91`. `--strict` also fails the run if the installed `ys` is not the pin. **The claim that CI installed the pinned `ys` is retracted below**: it ran `pip install yamlscript`, which ships no `ys` CLI, so on a fresh runner every probe would have exited 2. The install step now fetches the release asset the probes actually shell out to.
- A local probe run leaves the working tree clean when nothing changed: the evidence file is rewritten only when a verdict or output moved (`probes/run_probes.py`). Verified by running the suite twice with only the timestamp between them.
- The mutation check is non-destructive: it mutates a copy in a temp directory and runs with `--no-evidence`, so a checkout with uncommitted work is safe (`scripts/mutation_check.py:92-127`).
- The `range` mapping is falsifiable: reverting it to the inclusive YS form turns the v1.1.0 suite red — `scripts/mutation_check.py:30-42`, `:95-130`.
- The `mod` mapping is falsifiable: reverting `OP_MAP` to `%` turns `mod_negative` red — mutation `mod-reverts-to-remainder`.
- Both `let` fixes are falsifiable separately: reverting the binding vector to Clojure's `[k=v]`, and separately dropping the infix-body parentheses, each turn `let_value_pos` red — mutations `let-binding-form-reverts-to-clojure` and `let-infix-body-unwrapped`. The second one matters most: without the parentheses the value is wrong rather than an error, which no exit code would have caught.
- Map-literal key quoting is falsifiable: reverting it turns `map_kw` and `map_get` red — mutation `map-keys-unquoted`.
- String quoting is falsifiable: reverting to the old double-quote-on-`$` form turns `string_dollar` red — mutation `string-quoting-reverts-to-double`.
- 20 of the 23 probes compare exact stdout rather than a substring, decided by the expected file's own shape (`probes/run_probes.py`); all five suites are green — 10, 5, 2, 3 and 3 PASS — recorded in `convergence-claims/evidence/run-v1.0.0.json` and its four siblings. The v1.3.0 probes assert on values rather than on printed maps or on error text, because both of those moved between ys releases.
- The pack is loaded, not aspirational: eight rule files are present and referenced by `.compound-engineering/config.yaml:18-19`, listed at `compound-packs/yamlscript-semantics/README.md:18-27`. Verified by inspection.
- `generate_tests.py` reproduces `test_suite/` byte-identically. Verified by diffing all 15 generated bodies against the tracked files.

## Known to Break

| Breakage | Status | Evidence |
|---|---|---|
| `let` in value position emitted Clojure's `[k=v]` binding form, which YS rejects, and an unparenthesized infix body, which YS silently evaluates as its last operand | FIXED | Both were one line each. The emitter's KNOWN marker claimed this needed statement/expression separation and could not be fixed without an emitter restructure; that was wrong, and the rule that now holds the corrected fact is `no-block-form-in-value-position.md`. Pinned by `let_value_pos` and two mutations |
| `TR01_workflow`, the only full query shape probed, ERRORed on that defect and was carried as `xfail` | FIXED | It XPASSED the day the emitter was fixed, which is what forced the xfail entry to be retired rather than left to rot. `convergence-claims/evidence/run-v1.0.0.json` now records 10 PASS |
| `probes/corpus/TR01_simple.clj`, a second copy of the same defect kept as a failure fixture | DELETED | Once the emitter was fixed it duplicated `TR01_workflow`'s passing body exactly, so it carried no information. The independent minimal witness is now probe `let_value_pos` in v1.3.0, which pins the same path in a shape small enough to read as the spec |
| The claim said SUSPECT because a permanent ERROR held it there | FIXED | The suite is green, so `claim_state=ACTIVE` is what CI publishes. Both claim files record the flip and the xfail interpretation in their corrections sections |
| `(:a m)` — keyword as a function — is not implemented, and emits `:a(m)`, which YS cannot resolve | KNOWN, not fixed | Found while writing `map_kw`. `(get m :a)` works and emits `m.a`. Not covered by any probe, because a failing probe cannot be added for it without the xfail machinery this repo just retired |
| `RENAMES["mod"]` is shadowed for the infix path, so no probe constrains it | UNTESTED | KNOWN marker inline at `clj-to-ys.py:307-310`; verified by mutating that entry alone and observing the suite stay green. Reachable via `(apply mod …)` |
| Nothing consumes the claim state, so "downstream workers stop" is untested | UNTESTED | `.github/workflows/probe.yml:22-23` exposes `claim_state`; no in-repo consumer |
| `REPORT.md` and the claim both record a probe run that is not the committed one | LABELED, historical | Banner at `REPORT.md` top + §3 note + "Corrections to this file" in the claim; stale counts marked historical rather than restated, since a new run cannot retroactively validate the 2026-10-05 run |
| `REPORT.md` §10 called that same run "9 PASS, 1 FAIL"; the committed file says ERROR | FIXED | Now reads ERROR, matching `convergence-claims/evidence/run-v1.0.0.json` |
| Claim evidence refs pointed at `probes/compositions/`, a directory that does not exist | FIXED | `convergence-claims/cljys-calyx-query.md` § Evidence References now names `probes/corpus/`; correction recorded in its new corrections section |
| `REPORT.md` claimed the CHALLENGE path was tested and "PASSED" | FIXED (retracted in place) | `REPORT.md` §6 now reads "NOT RUN — no such test exists", with the original text retained as a record; §5 and §9 corrected to match |
| `probes/corpus/TR01.clj` and `probes/expected/TR01.json` are read by nothing | KNOWN, retained deliberately | No `manifest.json` entry. `TR01.clj` is the ancestor of `test_queries/find_dependents.clj` — research material, not dead code. Classified at `REPORT.md` § "Coverage gaps still open" |
| `014_maps`: a map literal emitted `hash-map(a 1 b 2)`, so YS resolved the keys as symbols | FIXED | `_token_expr` strips the `:` from a keyword, so the map branch passed a bare identifier to `hash-map`. Now quoted. Pinned by `map_kw` and `map_get` and mutation `map-keys-unquoted`; the tree's only map literal before that was the one in `014_maps.clj`, which is why nothing caught it (rule 1, `CODING_STANDARDS.md:6-11`) |
| `range_workflow` asserts one substring (`"count=4"`) and would pass on almost any wrong output | UNTESTED | `probes_v1_1/expected/range_workflow.json`; comparison shape at `probes/run_probes.py`. Frozen suite — fixing it needs a new version |
| | `TR01_simple` and `TR01_workflow` assert substrings, not exact output | UNTESTED | `probes/expected/TR01_simple.json`, `TR01_workflow.json`. Frozen v1.0.0 suite. `let_value_pos` in v1.3.0 pins the same construct with exact output, so the shape is covered — just not these two files |
| **Two different files were both named `run-v1.1.0.json`** | FIXED | The superseded twin moved to `convergence-claims/evidence_archive/run-v1.1.0.json`, under a name that cannot be mistaken for the canonical `convergence-claims/evidence/run-v1.1.0.json`, and it is older in schema and reports `range_nested` PASS on output containing four extra `(nil nil nil nil)` lines |
| The previous README claimed an LLM normalization front-end | FALSE | No prompt, model config, or network call exists in the tree; `clj-to-ys.py:16-19` |
| The previous README claimed `ys -c` produces a native binary | FALSE | `ys --help`: `-c, --compile  Compile YS to Clojure`; native binary is `-b, --binary`. No GraalVM in this repo |
| The documented install (`pip install yamlscript==0.2.8`) does not install the `ys` CLI, so neither a fresh clone nor CI could run a single probe | FIXED | The PyPI package ships `libys` + a Python binding and declares no entry points; verified by running it in a fresh venv, where `make probe` exits 2 telling you to run the command you had just run. The CLI is the release asset `ys-<version>-linux-x64.tar.xz`; README and `.github/workflows/probe.yml:33-46` now use it |
| `run_tests.sh` could not fail a build | FIXED | It exits on the verdict rather than on its last command, and the CI step that ran it non-gating now gates. 15 passed, 0 failed |
| The pack path was wrong in two docs (`.ce/packs/…`, real path `compound-packs/…`) | FIXED | `REPORT.md` §11 and `CODING_STANDARDS.md:17` now name `compound-packs/`, matching `.compound-engineering/config.yaml:19` |
| The pack rule `collection-literals-need-plus-prefix.md` documented a map form YS rejects (`m =: +{a: 1, b: 2}`) and a comma restriction that does not exist | FIXED | Both claims were wrong on execution, though right if you believe the YS docs; corrected in place with a dated `## Corrections` section, alongside the `let` facts in `no-block-form-in-value-position.md`. The pack README now says how a correction is recorded |
| YS evaluates an unparenthesized infix `let` body as its last operand: `(let [n 3] n + 1)` is `1` | KNOWN, upstream | YS's bug, worked around in the emitter by parenthesizing an infix body, on 0.2.8 and 0.3.5 alike. Not a YS documentation question — it is a wrong value with no error. Draft issue in `docs/clojure-vs-ys-gotchas.md` |
| `.compound-engineering/config.yaml` declares `docs_root: docs` | ENFORCED-ish | `docs/` now exists (`docs/clojure-vs-ys-gotchas.md`); the config comment says CE writes there, not that it is already populated |

## Repository Structure

```
cljys/
├── clj-to-ys.py              The transpiler. Not importable; CLI only. The system under observation.
├── probes/                   Probe suite. manifest.json is the single source of truth; run_probes.py is the one runner.
├── probes_v1_1/              Frozen v1.1.0 corpus + expected, in a second directory so v1.0.0 stays byte-identical.
├── probes_v1_2/              Same convention for v1.2.0 (mod with a negative dividend, _binding_coll).
├── probes_v1_3/              Same convention for v1.3.0 (let in value position, map-literal keys).
├── probes_v1_4/              Same convention for v1.4.0 (string quoting, multi-arg print).
├── KNOWN_ISSUES.md           Assumptions that still fail, with how they surface.
├── convergence-claims/       Hand-written claims (expire when the suite goes red) + generated evidence/*.json.
├── convergence-claims/evidence_archive/   Superseded runs, kept verbatim under their own name. Never cited.
├── compound-packs/           The knowledge layer: 8 hand-written YS↔Clojure equivalence rules. Live; config points here.
├── docs/                     clojure-vs-ys-gotchas.md: the divergences, executed against ys 0.2.8 and 0.3.5, plus two upstream issue drafts.
├── scripts/                  mutation_check.py (proves the suite can fail), vendor_ce_skills.py (agent tooling).
├── .github/workflows/        probe.yml. The only CI. Probes, mutation check, input-boundary check and run_tests.sh — all four gating.
├── test_suite/               Generated corpus (generate_tests.py). 15 files. Not used by probes.
├── test_primitives/          Hand-written Clojure exercises. No runner references these.
├── test_queries/             Realistic query shapes. Not referenced by any runner; probes/corpus/TR01.clj is their ancestor.
├── spec.md                   YAMLScript knowledge base. Canonical for mappings — where it and the code disagree, it is right.
├── CODING_STANDARDS.md       13 rules, each one this repo has broken or could break invisibly.
├── REPORT.md                 Hand-written research report. Carries a staleness banner; §6 is a retraction, not a result.
├── calyx_mcp_v6.json         444 KB tracked JSON fixture. Two probes actually read it at runtime.
├── AGENTS.md                 Agent operating mode for this repo.
├── LICENSE                   MIT.
├── Makefile                  probe / mutate / test / counts / clean. No other build file exists.
├── run_tests.sh              Only aggregate runner over test_suite/. Gating; 15 cases.
├── generate_tests.py         Regenerates test_suite/.
├── .compound-engineering/    config.yaml; points at the pack above. docs_root: docs, which does not exist yet.
├── .ce/                      GITIGNORED vendored third-party checkout. Its README documents paths that don't exist. Not project code.
├── .cljys/                   GITIGNORED local venv. Not on PATH; `ys` is installed globally instead.
├── .opencode/skills/         Generated from .ce/ by scripts/vendor_ce_skills.py. Do not hand-edit.
├── results/                  GITIGNORED run_tests.sh output. Mixed-vintage: 001_*.ys is newer than the rest.
├── test.clj / test.ys / debug.ys   GITIGNORED scratch from manual poking.
└── __pycache__/              GITIGNORED.
```

### Three kinds of probe artifact, not to be conflated

| Kind | Where | Expected verdict | Editable |
|---|---|---|---|
| **Regression suite** | entries in `probes/manifest.json` | passes | corpus/expected are frozen; changes need a new suite version |
| **Failure fixture** | a manifest entry carrying `"status": "xfail"` | *fails*, by design, as XFAIL | yes, if it still reproduces the defect it names |
| **Historical record** | `convergence-claims/evidence/`, `convergence-claims/evidence_archive/` | immutable | never — regenerated only by running the probes |

The middle row is empty right now, and that is the point of it. Two probes
carried `xfail` on 2026-10-16 while the `let` defect was open; when it was fixed
they XPASSED, which failed the run until the entries were deleted
(`probes/run_probes.py`). An expected-failure row that nothing watches
is how a known defect becomes an accepted one — so it fails CI when it stops
failing, and the standing instruction is to fix the probe rather than add a row.

A file in `probes/` that no manifest entry names is not automatically dead
code. `probes/corpus/TR01.clj` is the current example: it is the ancestor of
`test_queries/find_dependents.clj`. The second one, `probes/corpus/TR01_simple.clj`,
was deleted on 2026-10-17 — once the emitter was fixed it duplicated
`TR01_workflow`'s passing body exactly, and the independent minimal witness for
the same path is now probe `let_value_pos`.

## Contribution Guidelines (Failure-First)

Prioritized:

- A reproducible breakage: corpus file, expected file, `manifest.json` entry,
  and the diff that shows the wrong output (`CODING_STANDARDS.md:6-11`).
- A mutation that proves a fix causal, not a claim that it works
  (`scripts/mutation_check.py:30-42`).
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

## Notes on the Reports

Generated artifacts, all produced by `python3 probes/run_probes.py`:

- `convergence-claims/evidence/run-<version>.json` — one file per suite.
  Contains `timestamp`, `provenance` (`ys_version`, `python_version`,
  `transpiler_sha256`), per-probe `input`, exit codes, typed `reason`,
  `expected_output`, `actual_output`, `diff`, `status`, and `suite`
  (`probes/run_probes.py`). Regenerating them is the only correct way to change
  them; they are tracked on purpose (`.gitignore:65-70`) and are rewritten only
  when a verdict or output actually changed, so an unchanged run leaves the
  `timestamp` alone and the tree clean. The `timestamp` is the last content
  change, not the last run.
  Never hand-edit one to make a claim line up (`CODING_STANDARDS.md:43-44`).
- `convergence-claims/evidence_archive/run-v1.1.0.json` — a superseded run in an
  older record schema (no `input`, `kind`, or `passed` fields), whose
  `range_nested` entry reports PASS on an `actual_output` containing four extra
  `(nil nil nil nil)` lines. It used to sit at
  `convergence-claims/evidence_v1_1/run-v1.1.0.json`, one directory away from
  the canonical file and identical in name; it moved so no second file answers
  to `run-v1.1.0.json`. Both were never hand-edited.
- Hand-written, not generated by anything: `REPORT.md`,
  `convergence-claims/*.md`. Their `- current state:`, `- latest probe run:`,
  and `- probe summary:` fields are placeholders no script ever rewrites, which
  is how `convergence-claims/cljys-calyx-query.md:31` came to disagree with the
  evidence file it names three lines above.
- `results/*.ys` — `run_tests.sh` output. Gitignored, unreviewable, and mixed
  vintage: `results/001_basic_assignment.ys` is newer than the rest of the
  directory.

## Safety Claims vs Ground Truth

| Claim | Status | Evidence |
|---|---|---|
| An LLM front-end normalizes Clojure into a canonical subset before the emitter | FALSE | Nothing in the tree implements it; `clj-to-ys.py:16-19` |
| The canonical-subset rules "are handled automatically by the LLM front-end prompt" | FALSE | No prompt artifact exists; the rules are prose in `spec.md:244-291` |
| `ys -c` compiles to a standalone native binary via GraalVM | FALSE | `ys --help` (`-c` compiles to Clojure; `-b` is binary); no GraalVM here |
| The emitter is deterministic | ENFORCED | `clj-to-ys.py:16-19`: `re`, `sys`, `argparse`, `typing` only; no clock, RNG, or network |
| The probe suite is "independently verifiable; probes never assume cljys correctness" | PARTIAL | True of expectations (`probes/expected/*.json` are hand-written), but `TR01_simple`, `TR01_workflow`, and `range_workflow` assert substrings (`probes/run_probes.py`) and the TR01 probes read a 444 KB fixture from the repo root (`probes/manifest.json:92-105`, cwd pinned at `probes/run_probes.py`) |
| When probes fail the claim becomes SUSPECT and downstream workers stop | PARTIAL | The transition is real and mechanical (`.github/workflows/probe.yml:75-84`, `:86-91`); no worker exists to stop, so the second half is untested. `REPORT.md` §5, §6 |
| The CHALLENGE path was tested and passed | RETRACTED | `REPORT.md` §6 now records it as never run; no test file implements it. Steps 1 and 3 map to real CI logic, steps 2 and 4 have no implementation here |
| Claim evidence refs point at existing paths | TRUE | Fixed: the v1.0.0 claim named `probes/compositions/`, which does not exist; it now names `probes/corpus/`, verified against the tree. The v1.1.0 claim was already correct |
| A green suite is falsifiable | PARTIAL | Six mutations, on a temp copy so it runs anywhere. Still uncovered: no mutation covers `RENAMES`, whose `mod` entry is shadowed for the infix path, and the inclusive-range emission at `clj-to-ys.py:613` is probed by `binding_coll` but unmutated |
| Corpus and expected files are frozen and versioned | ENFORCED | Each new probe went into a new suite version with its own corpus and expected files (`probes/manifest.json:24-28`), and no existing `expected/*.json` was ever edited to make a suite pass. v1.1.0/v1.2.0/v1.3.0 live in forked directories so the earlier ones stay byte-identical |
| Version pinning is in one place | ENFORCED | `probes/manifest.json:3`, read by `probes/run_probes.py` and `.github/workflows/probe.yml:42` |
| The `ys` version is enforced, not just recorded | ENFORCED in CI | `--strict` fails the run on a mismatch (`probes/run_probes.py`) and CI passes it; locally a mismatch still warns and writes evidence the claims would then cite. Both are re-verified against 0.3.5, where every semantic this repo pins is unchanged but error wording and map print order are not (`docs/clojure-vs-ys-gotchas.md`) |
| The CI gate executes | RETRACTED, then fixed | **Retracted 2026-10-17.** This read ENFORCED on the strength of `REPORT.md` §11's "five gate defects fixed". It was not true: §11 had made CI install `ys` with `pip install yamlscript`, which installs `libys` plus a Python binding and **no `ys` binary** — the PyPI package declares no entry points. On a fresh runner every probe would have hit `ys is not on PATH` and exited 2, so the job would have failed for the wrong reason and `claim_state` would have read SUSPECT. Verified by running the documented install in a clean venv. Both the README and `REPORT.md` §11 now carry this correction, and the install step fetches the release asset instead. What remains unverified: no successful run of the workflow has been observed, only that its inputs are now correct |
| `mod` maps to YS `%%` | TRUE | `RENAMES` and `OP_MAP` both map it to `%%` (`clj-to-ys.py:311`, `:353`), matching `spec.md:141`. Pinned by `mod_negative` and proven by the `mod-reverts-to-remainder` mutation. The `RENAMES` entry specifically remains unprobed — see § "Known to Break" |
| The pack contains 8 rules, 0 skipped | ENFORCED | Eight rule files present; `compound-packs/yamlscript-semantics/README.md:18-27` |
| The pack is consulted by tooling | PARTIAL | `.compound-engineering/config.yaml:18-19` wires it for CE skills; the transpiler itself never reads it |
| Every emitter branch has a probe | UNVERIFIED | `CODING_STANDARDS.md:6-11` states the rule; 23 probes over 1200 lines, and `REPORT.md` §8 lists unenumerated compositions. The map-literal branch had no probe at all until 2026-10-17, which is how `014_maps` reached the tree |
| Agent tooling is reproducible from the vendored source | PARTIAL | `--check` passes in a checkout that has `.ce/` (verified: "15 vendored skills match source"), but `.ce/` is gitignored (`.gitignore:81`), so from a fresh clone the source is absent, the script cannot run, and the committed `.opencode/skills/` cannot be regenerated |

## Current Risks (Ranked by Likelihood)

1. ✅ ~~`mod` silently produces a wrong sign on negative operands~~ — **fixed**.
   Both maps now emit `%%`; `mod_negative` pins it with a negative dividend and
   mutation `mod-reverts-to-remainder` proves the probe catches a regression.
   `RENAMES`'s entry is still unprobed.
2. ✅ ~~CI is red on every push~~ — **fixed**, then un-fixed and fixed again: the
   `xfail` mechanism made the suite green while the emitter was still broken,
   and separately the CI install step never actually installed `ys` (see the
   retraction above). Both are resolved, and the standing risk they leave is the
   honest one — a green gate that was green for the wrong reason, which is what
   `--strict`, XPASS-fails-the-run, and the mutation check exist to catch.
3. ❗ `let` in value position blocks the only realistic query shape the suite
   exercised (`clj-to-ys.py:832-856`; `probes/workflows/TR01_workflow.clj`).
   ✅ **Fixed 2026-10-17** — and the fix was one line each, not the emitter
   restructure the old KNOWN marker insisted on: `[k=v]` became `[k v]`, and an
   infix body is parenthesized. Two mutations prove both. What remains is the
   trap underneath it: YS mis-evaluates an unparenthesized infix `let` body, so
   this class of defect is silent rather than loud.
4. ❓ No lint, no type checking, and an emitter change that compiles can still
   produce wrong output — caught only if someone remembers to add a manifest
   entry. `014_maps` was the proof (one map literal in the tree, no probe, a
   wrong emission) and the `let` infix body is the sharper one: that defect
   produced a plausible wrong number with no error at all. Both are pinned now;
   the next unemitted branch will not be, unless a mutation covers it.
5. ❓ The evidence files cited by both convergence claims still name one run
   ("the cited run") that any later run rewrites in place. Rewriting only on a
   real change makes the diff meaningful again, but the ambiguity remains:
   `re-run the suite` and `the evidence has not changed` are different
   operations, and only one of them is visible in the tree.
6. ❓ `REPORT.md` and the claim prose are hand-maintained with no generator and
   no reviewer, so they drift silently. Both now carry staleness banners, which
   slows the drift but does not stop it.
7. ❗ 23 probes cover a fraction of the emitter's forms; the enumeration itself
   is incomplete (`REPORT.md` §8).
8. ✅ ~~The decorative-CI gate~~ — five separate defects were fixed
   (`REPORT.md` §11, `.github/workflows/probe.yml:33-105`), and then a sixth
   surfaced underneath them: the install step fetched a Python package that
   ships no `ys` CLI, so the gate still could not have run. That is the
   retraction recorded in § Safety Claims.
9. ✅ The `range` end-semantics bug is fixed, probed, and mutation-proven
   (`REPORT.md` §10, `probes_v1_1/`, `scripts/mutation_check.py`).
10. ❓ Eleven duplicated probe scripts were replaced by a manifest
    (`CODING_STANDARDS.md:12-14`), and orphan corpus files are now classified
    rather than merely noted: `probes/corpus/TR01.clj` is an ancestor of
    `test_queries/`, and `probes/corpus/TR01_simple.clj` was deleted once it
    became a byte-identical duplicate of a passing probe.

## This Is a Survival Lab

The transpiler is the specimen; the repo is built to break it cleanly, record
how it broke, take pressure from outside, and notice when its own meaning
drifts.

- **Break cleanly.** Every probe verdict lands as machine-written JSON with the
  input, the expected output, the actual output, and a diff
  (`probes/run_probes.py`), so a failure is a data record, not a
  transcript someone has to reconstruct.
- **Record its own errors.** A probe that produces invalid YS is recorded as
  ERROR with `ys`'s stderr, not as an output mismatch
  (`probes/run_probes.py`); `TR01_workflow` carries the real cause
  because of this. A probe the manifest expects to fail carries that verdict as
  XFAIL instead, so a known defect and a new one are never the same colour.
- **Invite outside pressure.** A claim is scoped, conditional, and cites a
  specific run; it expires when the suite regresses rather than requiring
  someone to notice (`convergence-claims/cljys-calyx-query.md:7-13`).
- **Track semantic drift.** Clojure and YS share enough syntax that code
  compiling in both can mean different things; each known divergence is a
  frozen, versioned rule plus a probe (`compound-packs/yamlscript-semantics/README.md:18-27`).
- **Prove its own green is falsifiable.** Two mutations reintroduce fixed
  defects and assert green-then-red, in CI, so "everything passes" is a result
  rather than an absence of information (`scripts/mutation_check.py`,
  `.github/workflows/probe.yml:63-66`).

It does not guarantee correct transpilation. Twenty-three probes and five
mutations against a 1200-line emitter is a floor, not a proof — nothing is
marked `xfail`, and `make counts` is where those numbers come from.