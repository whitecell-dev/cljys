# Coding standards — cljys

Reviewed against by `/ce-review`. Each rule here is one this repo has actually
gotten wrong, or one whose violation would be invisible in the output.

## Probes

1. **No emitter branch without a probe.** Any new branch in `clj-to-ys.py` that
   can change generated output needs a corpus file, an expected file, and a
   `probes/manifest.json` entry. The bug class here is silent-wrong-output, so
   "it compiles" is not evidence.
2. **A probe is a manifest entry, never a script.** Adding a probe means adding
   data to `probes/manifest.json`. The eleven near-identical `*_probe.py`
   scripts were deleted for this reason; `git log` still has them.
3. **A new form family needs its equivalence rule first.** Before implementing
   a Clojure construct, add a rule to
   `.ce/packs/yamlscript-semantics/` stating how it maps and where Clojure and
   YS disagree. Implementation follows the rule, not the other way round.
4. **Corpus and expected files are frozen.** A wrong expected output is fixed by
   adding a new suite version, never by editing an existing `expected/*.json`.
   If the transpiler is right and the expectation wrong, that is a finding, not
   an inconvenience.
5. **Probes run the real `ys`.** No probe may assert on emitted YS text alone;
   it must execute and compare output. Syntactic validity is not semantics.

## Semantic equivalence

6. **Verify YS behavior, do not reason about it.** `ys -p -e '<expr>'` settles
   what an operator or form does in about a second. Two mappings in this repo
   were wrong in ways that reading YS's docs would not have caught.
7. **Clojure and YS are not the same language.** They share enough syntax that
   a construct can compile in both and mean different things. `range` bounds,
   `mod` vs `rem` sign, and block-form placement have all bitten here.
8. **Reject what the runtime cannot do.** SCI has no macros, dynamic vars, or
   reader macros. An error naming the construct beats a plausible-looking
   emission that runs and disagrees.

## Change discipline

9. **A fix is not done until a mutation proves it.** Add the reverted form to
   `scripts/mutation_check.py` and observe the suite go red, then green.
   `REPORT.md` section 10 claims this was done by hand; it is mechanical now.
10. **Re-running a suite rewrites its evidence file.** Evidence is generated,
    not authored. Never hand-edit `convergence-claims/evidence/run-*.json`.
11. **Pin `ys` in one place.** The version lives in `probes/manifest.json` and
    CI reads it from there. Two copies of a version pin is one drift away from
    incomparable evidence.

## Documentation

12. **A command in the README must run.** It names `clj_to_ys.py`; the file is
    `clj-to-ys.py`. Check the filename against the tree before publishing.
13. **`spec.md` is canonical for mappings; the code is not.** Where they
    disagree, `spec.md` is right and the emitter is the bug — `RENAMES` maps
    `mod` to `%` where the spec says `%%`. Fix the code, not the spec.
