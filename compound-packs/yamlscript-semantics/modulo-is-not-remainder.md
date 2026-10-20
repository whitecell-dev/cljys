---
title: mod and rem differ in sign, so mod maps to %% and only rem maps to %
applies_when:
  - adding or changing arithmetic, modulo, or remainder handling
  - emitting % or %% from a transpiled expression
  - writing a probe that covers modulo or negative operands
tags: [arithmetic, mod, rem, sign, semantics]
---

Clojure's two modulo forms disagree on negative operands, and YS's two
operators disagree the same way — so the mapping is one-to-one and getting it
wrong is silent:

| Clojure | Result | YS operator | Result |
|---|---|---|---|
| `(rem -7 3)` | `-1` | `%` | `-1` |
| `(mod -7 3)` | `2` | `%%` | `2` |

`rem` is truncated division (sign follows the dividend); `mod` is floored
division (result takes the divisor's sign). YS `%` truncates and YS `%%` floors,
so `rem` → `%` and `mod` → `%%`.

**Fixed 2026-10-17:** `RENAMES` in `clj-to-ys.py` maps `mod` to `%%` and `rem` to
`%`. Positive operands alone would not have caught the old defect, so the probe
uses a negative dividend (`mod_negative`) and the mutation check reverts the
mapping to `%`.

`spec.md` records the correct mapping (`mod` → `%%`); `RENAMES` disagrees with
it. When the two conflict, `spec.md` is right and `RENAMES` is the bug.

Do not "simplify" by dropping one of the two operators. They are different
functions and Clojure callers rely on the difference.