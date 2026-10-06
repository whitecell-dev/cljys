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
  - probes/compositions/BUG01
  - probes/compositions/PA01
  - probes/compositions/TR02
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

## Notes
The workflow-level claim is written as specified. The evidence references point to
a specific probe run with concrete outputs (raw evidence), not the abstract suite.
