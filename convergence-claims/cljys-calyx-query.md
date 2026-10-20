# Convergence Claim: cljys.calyx-query

## Claim Metadata
- id: cljys.calyx-query
- version: v1.0.0
- scope: cljys.calyx-query
- claim: >
  cljys version X is authorized for CALYX query pipelines,
  valid while probe suite Y passes on corpus Z.
  Exploratory queries only. Production use requires a
  separate authorization.
- constraint: exploratory queries only
- drift_condition: probe suite must pass without regression

## Evidence References
- evidence_refs:
  - convergence-claims/evidence/run-v1.0.0.json
  - probes/corpus/BUG01
  - probes/corpus/PA01
  - probes/corpus/TR02
  - probes/primitives/P01_def
  - probes/primitives/P02_arithmetic
  - probes/primitives/P06_each
  - probes/primitives/P11_range
  - probes/primitives/P12_threading
  - probes/workflows/TR01_simple

## Status
- current state: ACTIVE (probe suite v1.0.0 passes; no probe is xfail, see the corrections section)
- latest probe run: run-v1.0.0.json (last content change; the file now records provenance)
- probe summary: 10 PASS, 0 FAIL, 0 ERROR, 0 UNKNOWN, 0 XFAIL

### Corrections to this file

This file is hand-maintained and nothing regenerates it. Two defects were
corrected on 2026-10-17; both are recorded here rather than silently edited.

- **Evidence ref paths were wrong.** They named `probes/compositions/…`, a
  directory that does not exist. The composition probes live in
  `probes/corpus/`. `REPORT.md` section 11 recorded this class of defect as
  fixed, but only in the v1.1.0 claim; this file was missed.
- **The probe summary used to be stale.** It said "5 PASS, 5 FAIL, 0 ERROR",
  which described the 2026-10-05 run, not the committed
  `convergence-claims/evidence/run-v1.0.0.json`. It now mirrors the committed
  file. The evidence remains authoritative and its verdicts churn whenever an
  output moves; do not treat the summary as a live reading. The current state
  is ACTIVE.
- **The state flipped twice on 2026-10-17, and the scope with it.** First
  `TR01_workflow` and `TR01_simple_let` were marked `"status": "xfail"`, so the
  suite exited 0 and CI began publishing `claim_state=ACTIVE` while the emitter
  was still broken — a carve-out, recorded in that revision of this file. Then
  the defect itself was fixed (the `let` binding form, plus an infix body YS
  silently mis-evaluates), both probes XPASSED, and the entries were deleted.
  The claim's wording never needed the carve-out: **ACTIVE here now means every
  probe passes**, with no expected-failure exemptions. The superseded "SUSPECT"
  line above is kept as the record of the state before that change.
- **This claim was never enforced by a gate that ran.** It said SUSPECT from the
  start because the suite was red, which read as a gate keeping the claim honest.
  It was not: CI could not install `ys` at all until 2026-10-17 (the install step
  pip-installed a package that ships no CLI binary), so no workflow run had ever
  evaluated it. The state in this file was maintained by hand, by the same person
  who wrote the claim. See `REPORT.md` §11's retraction.

## Notes
The workflow-level claim is written as specified. The evidence references point to
a specific probe run with concrete outputs (raw evidence), not the abstract suite.

Nothing in this repository consumes the claim state. `claim_state` is published
as a CI job output (`.github/workflows/probe.yml:13-14`) but no worker reads
it, so "the claim becoming SUSPECT stops downstream work" is unverified here —
see `REPORT.md` section 6.
