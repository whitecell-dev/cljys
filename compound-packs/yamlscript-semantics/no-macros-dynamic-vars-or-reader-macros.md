---
title: The YS runtime has no macros, dynamic vars, or reader macros, so such input must be rejected not transpiled
applies_when:
  - adding support for a new Clojure form
  - deciding whether an unsupported construct should error or emit something approximate
  - reviewing a transpiler change that widens the accepted input
tags: [macros, dynamic-vars, reader-macros, sci, rejection, trust-boundary]
---

YS compiles to Clojure and runs on SCI. That runtime has no macroexpansion
phase, no dynamic variables, and no reader macros. Input using them cannot be
transpiled to anything meaningful:

| Construct | Status |
|---|---|
| `defmacro` | unsupported — there is no expansion phase |
| `(def ^:dynamic v ...)` | unsupported — SCI has no dynamic vars |
| `#(...)` anonymous fn literal | unsupported — normalize to `(fn [x] ...)` |
| Multi-arity `(defn f ([x] ...) ([x y] ...))` | unsupported — use default args: `(defn f (x y 0) ...)` |
| `clojure.string/join` (qualified) | normalize to the unqualified builtin `join` |

**Reject, do not approximate.** The transpiler's contract is that a Clojure
subset compiles to a program with identical observable behavior. Emitting a
plausible-looking YS body for a macro is worse than erroring, because the
result compiles, runs, and quietly disagrees with the input — the exact
`range`-class failure this pack exists to prevent.

So an unsupported form is an error with the form named, not a fallback
emission. `README.md` documents the supported subset; `spec.md`'s
`forbidden_patterns` is the canonical list. When adding a form family, check it
against this table first: if SCI cannot run the concept, the right answer is a
clear error at the boundary.