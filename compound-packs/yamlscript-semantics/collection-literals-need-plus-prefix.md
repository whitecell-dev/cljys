---
title: Collection literals need the + prefix and cannot be passed inline as call arguments
applies_when:
  - adding or changing vector, map, or set literal emission
  - passing a literal collection to a function or an indexing operation
  - debugging YS output where a collection literal is rejected or misread
tags: [literals, vector, map, hoisting, compilation]
---

A Clojure collection literal is not a YS collection literal. Two requirements,
both easy to get right individually and wrong together.

**1. The `+` prefix is mandatory.** `[1 2 3]` is not a vector in YS; `+[1 2 3]`
is. Same for maps: `+{a: 1, b: 2}`.

```
(def xs [1 2 3])     →  xs =: +[1 2 3]
(def m {:a 1 :b 2}) →  m =: +{a: 1, b: 2}
```

**2. A literal is only safe as an assignment RHS.** Map and vector literals are
forbidden as function arguments and inside nested expressions. Hoist first:

```
# wrong: literal in argument position
say: nth(+[10 20 30], 1)

# right: hoisted, then referenced by name
row =: +[10 20 30]
say: nth(row, 1)
```

Also inside literals: **no commas** in vectors (`+[1 2 3]`, not `+[1, 2, 3]`) and
a comma *is* the map separator (`+{a: 1, b: 2}`).

**No implicit calls.** Clojure lets a vector or map be invoked as a function;
YS does not. Index with `nth`:

```
(nth xs 0)        ✓
(xs 0)            ✗  → (nth xs 0)
```

That rewrite is the LLM front-end's job per `README.md`'s canonical
specification, but the emitter must still never produce the implicit form — a
normalization miss upstream should not become a wrong YS program downstream.

`spec.md` is the full table of allowed and forbidden positions; it is storage,
not a rule.