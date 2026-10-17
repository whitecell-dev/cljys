---
title: Collection literals need the + prefix, maps need hash-map, and nothing is a call argument
applies_when:
  - adding or changing vector, map, or set literal emission
  - passing a literal collection to a function or an indexing operation
  - debugging YS output where a collection literal is rejected or misread
tags: [literals, vector, map, hoisting, compilation]
---

A Clojure collection literal is not a YS collection literal. Three requirements,
and the second one is why the first looks like it should be enough.

**1. Vectors and sets need the `+` prefix.** `[1 2 3]` is not a vector in YS;
`+[1 2 3]` is. Without the prefix: "Sequences (block and flow) not allowed in
code mode".

```
(def xs [1 2 3])     →  xs =: +[1 2 3]
```

**2. Maps have no literal form at all in code mode — use `hash-map` with quoted
keys.** This is not the manual's advice being second-guessed; it is what YS does.
`!ys-0` forbids flow mappings everywhere, including as an assignment RHS, so
every one of these fails with "mapping values are not allowed here":

```
m =: +{a: 1, b: 2}      # assignment RHS - what the YS docs show
say: +{a: 1, b: 2}     # expression position
m =: +{a: 1}           # block form inside a flow
```

What does work, in code mode, in any expression position:

```
(def m {:a 1 :b 2})     →  m =: hash-map("a" 1 "b" 2)
```

Two details that are easy to get wrong:

- **Quote the keys.** `hash-map(a 1)` makes YS resolve `a` as a symbol and fail
  with "Could not resolve symbol: a" (wording differs by version). The failure
  looks like it is about the whole map, not the key.
- **Do not print a map in a test.** YS maps are unordered: the same map prints
  `{a 1, b 2}` on ys 0.2.8 and `{b 2, a 1}` on 0.3.5. Assert on a lookup, never
  on printed map text.

**3. A literal is only safe as an assignment RHS.** Map and vector literals are
forbidden as function arguments and inside nested expressions. Hoist first:

```
# wrong: literal in argument position
say: nth(+[10 20 30], 1)

# right: hoisted, then referenced by name
row =: +[10 20 30]
say: nth(row, 1)
```

**No implicit calls.** Clojure lets a vector or map be invoked as a function;
YS does not. Index with `nth`:

```
(nth xs 0)        ✓
(xs 0)            ✗  → (nth xs 0)
```

That rewrite is the emitter's job. The emitter must never produce the implicit
form — a normalization miss upstream should not become a wrong YS program
downstream.

## Corrections

- **2026-10-17.** Two claims in the previous version of this rule were wrong, and
  both were caught by executing YS rather than reading it (`CODING_STANDARDS.md`
  rule 6). It showed `m =: +{a: 1, b: 2}` as the map mapping — that form is
  rejected in code mode, and the emitter's inline comment had already recorded
  the discovery the rule contradicted. It also said "no commas in vectors
  (`+[1 2 3]`, not `+[1, 2, 3]`)"; `+[1, 2, 3]` is `[1 2 3]` on both 0.2.8 and
  0.3.5, so commas are allowed and the restriction was invented. Both are
  verified in `docs/clojure-vs-ys-gotchas.md`. The "no implicit calls" rule and
  the `+` prefix requirement were already right and are unchanged.
- The comma claim is documented rather than probed: Clojure treats `,` as
  whitespace, so a transpiled corpus can never contain a comma inside a vector
  literal and the probe harness cannot reach the case at all. Evidence for it is
  the reproduction in `docs/clojure-vs-ys-gotchas.md`, not a probe.