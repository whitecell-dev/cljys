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
- current state: SUSPECT (based on latest probe run v1.0.0 showing failures)
- latest probe run: run-v1.0.0.json (2026-10-05T05:08:21.208012Z)
- probe summary: 5 PASS, 5 FAIL, 0 ERROR

### Corrections to this file

This file is hand-maintained and nothing regenerates it. Two defects were
corrected on 2026-10-17; both are recorded here rather than silently edited.

- **Evidence ref paths were wrong.** They named `probes/compositions/…`, a
  directory that does not exist. The composition probes live in
  `probes/corpus/`. `REPORT.md` section 11 recorded this class of defect as
  fixed, but only in the v1.1.0 claim; this file was missed.
- **The probe summary is stale and is retained as history.** "5 PASS, 5 FAIL,
  0 ERROR" describes the 2026-10-05 run named above, not the committed
  `convergence-claims/evidence/run-v1.0.0.json`, and not any current run. The
  evidence file is authoritative and its verdicts churn on every run; do not
  treat this line as a live reading. Current state (SUSPECT) is still correct.

## Notes
The workflow-level claim is written as specified. The evidence references point to
a specific probe run with concrete outputs (raw evidence), not the abstract suite.

Nothing in this repository consumes the claim state. `claim_state` is published
as a CI job output (`.github/workflows/probe.yml:13-14`) but no worker reads
it, so "the claim becoming SUSPECT stops downstream work" is unverified here —
see `REPORT.md` section 6.
