# Convergence Claim: cljys.calyx-query (v1.1.0)

## Claim Metadata
- id: cljys.calyx-query
- version: v1.1.0
- scope: cljys.calyx-query
- claim: >
  cljys commit eee4c6fc2881af780e2da81232993a84652ec150 (with range fix) is authorized for CALYX query pipelines,
  valid while probe suite v1.1.0 passes on corpus v1.1.0.
  Exploratory queries only. Production use requires a
  separate authorization.
- constraint: exploratory queries only
- drift_condition: probe suite must pass without regression

## Evidence References
- evidence_refs:
  - probes_v1_1/run-v1.1.0.json
