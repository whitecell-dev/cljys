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

**Verified defect, currently unfixed:** `RENAMES` in `clj-to-ys.py` maps *both*
`mod` and `rem` to `%`. `(mod -7 3)` therefore transpiles to `-7 % 3`, which
evaluates to `-1` where Clojure gives `2`. Positive operands are unaffected,
which is why a probe with only positive operands passes and hides the bug — a
modulo probe must include a negative dividend.

`spec.md` records the correct mapping (`mod` → `%%`); `RENAMES` disagrees with
it. When the two conflict, `spec.md` is right and `RENAMES` is the bug.

Do not "simplify" by dropping one of the two operators. They are different
functions and Clojure callers rely on the difference.