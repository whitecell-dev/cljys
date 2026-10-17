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
  - convergence-claims/evidence/run-v1.1.0.json

## Status
- current state: ACTIVE (suite v1.1.0 passes, no xfail entries)
- latest probe run: run-v1.1.0.json (see the file's `timestamp`)
- probe summary: 5 PASS, 0 XFAIL, 0 ERROR

Added 2026-10-17. This claim had no Status section at all, which is how a claim
went from "written while red" to "cited by the README as authoritative" without
anything recording which it was. It was not wrong about its scope, only silent:
suite v1.1.0 is green and always has been. The same caveat as the v1.0.0 claim
applies — no workflow run had evaluated either of them until the CI install step
was fixed on 2026-10-17, so these states were hand-maintained.
