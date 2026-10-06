---
title: Clojure range excludes its end bound, so emit YS range() and never the .. form
applies_when:
  - adding or changing how a range expression is transpiled
  - iterating over a numeric range in a transpiled query
  - adding a loop, comprehension, or index-based iteration over numbers
tags: [range, iteration, semantics, off-by-one]
---

`(range a b)` is **exclusive** of `b` in Clojure: `(range 1 4)` is `(1 2 3)`.
The YS range form `(a .. b)` is **inclusive**: `(1 .. 4)` is `(1 2 3 4)`. YS's
`range(a, b)` function form is exclusive, matching Clojure.

Always emit the function form, never `..`:

| Clojure | Emit | Not |
|---|---|---|
| `(range 1 4)` | `range(1, 4)` | `(1 .. 4)` |
| `(range 5)` | `range(0, 5)` | — |
| `(range 1 10 2)` | `range(1, 10, 2)` | — |

This is the repo's one confirmed catastrophic mapping: it was wrong for all
three arities, and it produced programs that ran without error and emitted the
wrong number of iterations (`REPORT.md` section 10). Primitives that pass in
isolation can still compose into a wrong program — the failure appears at the
composition level, so a range probe needs a composition case, not just `(range 1
4)` alone.

There is one legitimate `..` emission: `_binding_coll` in `clj-to-ys.py`
converts a *contiguous* integer literal vector to `(first .. last)`, which is
correct precisely because a contiguous run's inclusive last equals the
exclusive `last + 1` that Clojure's `range` would have stopped at. Do not
generalize that to a non-contiguous vector.

Verify a change here by reverting it and confirming probes go red
(`scripts/mutation_check.py` does exactly this).