---
title: Clojure vs YAMLScript gotchas, verified against two ys releases
applies_when:
  - changing a mapping in clj-to-ys.py or a rule in compound-packs/
  - bumping the pinned ys version in probes/manifest.json
  - reading a YS error message and guessing which construct caused it
tags: [semantics, mapping, verification, gotchas, upstream]
---

Every claim here was executed, not reasoned about. Reproduce any row with the
recipe at the bottom; each one takes a second.

- Verified against **ys 0.2.8** (the pin in `probes/manifest.json:3`) via the CLI,
  using both the globally installed `ys` and a freshly extracted
  `ys-0.2.8-linux-x64.tar.xz` — byte-identical behaviour, so the two are the same
  build.
- Verified against **ys 0.3.5** (current release at the time of writing) via
  `libys.so` 0.3.5, because that release publishes the CLI for more platforms but
  the behaviour of the language is the same either way.

## The table

| Clojure / emitted YS | ys 0.2.8 | ys 0.3.5 | verdict |
|---|---|---|---|
| `range(1, 4)` (from `(range 1 4)`) | `(1 2 3)` | `(1 2 3)` | end is **exclusive** in both; `(1 .. 4)` is the inclusive trap |
| `-7 %% 3` (`mod`) | `2` | `2` | `%%` is floored, correct |
| `-7 % 3` (`rem`) | `-1` | `-1` | `%` truncates, correct |
| `(let [v=5] v)` — what the emitter used to write | `Error: let requires an even number of forms in binding vector` | same error | **fails in both**; fixed in the emitter 2026-10-17 |
| `(let [v 5] v)` — name/value binding | `5` | `5` | **works in both**, including in value position |
| `(let [n 3] n + 1)` — infix body, unparenthesized | `1` | `1` | **silently wrong in both**; `4` is correct. Fixed in the emitter by wrapping |
| `hash-map("a" 1 "b" 2)` | `{a 1, b 2}` | `{b 2, a 1}` | works; **key order is not stable across versions** |
| `hash-map(a 1 b 2)` — bare keys | `Error: Could not resolve symbol: b` | `Error: unable to resolve symbol: b` | **fails in both**; this was `014_maps`, fixed in the emitter 2026-10-17 |
| `m =: +{a: 1, b: 2}` | `Compile error: mapping values are not allowed here` | same class of error | flow mappings are impossible in code mode — see the correction in the pack rule |
| `+[1 2 3]` | `[1 2 3]` | `[1 2 3]` | `+` prefix required |
| `[1 2 3]` | `Compile error: Sequences (block and flow) not allowed in code mode` | same | ditto |
| `+[1, 2, 3]` | `[1 2 3]` | `[1 2 3]` | **commas are fine** — the pack rule says otherwise |
| `nth(+[10 20 30], 1)` | `Error: PersistentVector cannot be cast to Number` | `Error: cannot convert *lang.Vector to int64` | literal as a call argument is rejected |

## What this repo gets wrong in its own docs

Two claims in `compound-packs/yamlscript-semantics/collection-literals-need-plus-prefix.md`
are contradicted by the table:

1. **`m =: +{a: 1, b: 2}` does not work.** YS code mode rejected every flow
   mapping this repo tried — expression position, call argument, assignment RHS,
   and a block form nested inside a flow — always with "mapping values are not
   allowed here". The emitter's inline comment at `clj-to-ys.py:690-720` already worked
   this out; the rule was written from the YS manual rather than from `ys`.
2. **Commas in vectors are allowed.** `+[1, 2, 3]` is `[1 2 3]`, identical to
   `+[1 2 3]`. The rule's "no commas in vectors" is not a real constraint.

What the rule got right, and what `hash-map("a" 1 "b" 2)` rests on: the `+`
prefix is mandatory for collection literals, and a literal is not safe as a call
argument. Given that, **`hash-map` with quoted keys is not a workaround — it is
the only form found that works.** That is the answer to "what is idiomatic for a
map literal":

```
(def m {:a 1 :b 2})   →   m =: hash-map("a" 1 "b" 2)
```

with the caveat that a map literal key must be quoted, because a bare `:a`
transpiles to a bare `a` and YS resolves that as a symbol.

## `let` in value position: two defects, and the wrong one was diagnosed

`clj-to-ys.py:832-856` used to carry a KNOWN marker saying "YS rejects inline
`let` in value position, so any call argument containing a let breaks", and
`REPORT.md` described the fix as needing statement/expression separation in the
emitter. Both were wrong. What YS actually does:

```
!ys-0
say: (let [x 1] (str "a" x))     →  a1      # value position is fine
x =: 1
say: (let [v x] (+ v 1))         →  2       # and with a computed binding
!ys-0
say: (let [v=5] v)               →  Error: let requires an even number of forms
```

Note the space: `[v x]` works, `[v=x]` does not, and the error is a form-parity
complaint in both cases — `[v=x]` reads as one form, not two. Value position,
`fn` bodies and multi-form bodies are all fine on both releases; only the
binding *shape* is rejected.

**Defect 1, fixed 2026-10-17:** the emitter wrote Clojure's `name=init`, so
every value-position `let` ERRORed. The fix is one line — emit `[k v]`.

**Defect 2, found by fixing defect 1, still open upstream:** with the binding
fixed, an infix body is evaluated as its **last operand**:

```
!ys-0
say: (let [n 3] n + 1)           →  1        # WRONG; 4 is correct
say: (let [n 3] (n + 1))         →  4        # correct
say: (let [x 1 y 2] (+ x y))     →  3        # without parens: 2
```

Identical on 0.2.8 and 0.3.5. This one is worse than the first in every way that
matters here: no error, just a plausible wrong number, and no exit code anywhere
in the toolchain would have caught it. The emitter works around it by
parenthesizing an infix body — and only an infix body, since a bare `(n)` is a
call of `n`, which is not callable:

```
!ys-0
say: (let [n 3] (n))             →  Error: cannot apply non-function int64
```

Probe `let_value_pos` pins both halves, and mutations
`let-binding-form-reverts-to-clojure` and `let-infix-body-unwrapped` revert each
one separately to prove the workaround is load-bearing.

## Version sensitivity

Both releases agree on every semantic above, so the pinned-version warning in
`probes/run_probes.py:200-210` is about *comparability*, not about a behaviour
change. Two things do differ and will break exact-output probes:

- **Error wording.** "Could not resolve symbol" became "unable to resolve
  symbol"; runtime errors gained an " in main:" suffix. Any doc or probe matching
  an error string is version-fragile — which is why no probe in this repo asserts
  on one: `let_value_pos` and `map_kw` exist precisely to check the *value* the
  fixed forms produce rather than the message the broken ones produced.
- **Map print order.** `{a 1, b 2}` on 0.2.8, `{b 2, a 1}` on 0.3.5. A probe that
  `say`s a multi-key map will fail on a version bump for reasons that have
  nothing to do with the transpiler.

## Reproduce

```bash
YS_VERSION=0.3.5                       # 0.2.8 for the pinned column
curl -fsSL https://github.com/yaml/yamlscript/releases/download/$YS_VERSION/ys-$YS_VERSION-linux-x64.tar.xz | tar -xJ
printf '!ys-0\nsay: (let [v=5] v)\n' > /tmp/g.ys
./ys-$YS_VERSION-linux-x64/ys /tmp/g.ys
```

One row, one second, no judgement involved — the rule this repo calls
`CODING_STANDARDS.md:28-30`.

---

# Upstream issue drafts

Not filed. Both are drafts for [yaml/yamlscript](https://github.com/yaml/yamlscript).

## Draft 1 — `let` with an infix body silently evaluates to the wrong value

**Title:** `let` in expression position evaluates an unparenthesized infix body
as its last operand

**Severity:** silent wrong result. No error, no warning — a plausible number.

**Body:**

An infix expression in a `let` body, in expression position, evaluates to its
**last operand** rather than to the infix result:

```yaml
!ys-0
say: (let [n 3] n + 1)
```

```
1
```

`4` is correct. Adding one more operand moves the answer, which is what makes it
look like an infix result at a glance:

```yaml
!ys-0
say: (let [x 1 y 2] x + y)      → 2     # should be 3
say: (let [n 3] n + 1 + 2)      → 2     # should be 6
say: (let [n 3] (n + 1))        → 4     # parenthesized: correct
say: (let [n 3] (+ n 1))        → 4     # call form: correct
```

Verified on both 0.2.8 and 0.3.5. It is specific to `let` in expression position:
the same infix works everywhere else we tried — as a statement, as a `say`
argument, and as the argument of `when`/`if` (`n.when(n + 1)` is `4`).

Parenthesizing the body is a complete workaround, and it is what our transpiler
now emits. One caveat for anyone writing the workaround by hand: only an infix
body may be wrapped, since `(let [n 3] (n))` is a call of `n` and fails with
"cannot apply non-function int64".

Why it matters beyond our case: this is the shape of bug that survives a test
suite. Our probes all passed with `(let [x 1 y 2] (+ x y))` returning `2`, because
nothing asserted the *value* — the surrounding query shape only checked that a
module count was a non-empty string.

## Draft 2 — clearer error for Clojure-style `name=init` in a `let` binding vector

**Title:** `let` binding error message does not mention the accepted shape

**Body:**

A binding vector written in Clojure's `name=init` form fails with a message that
points at the wrong thing:

```yaml
!ys-0
say: (let [v=5] v)
```

```
Error: let requires an even number of forms in binding vector
```

The parity complaint is accurate — `[v=5]` is one form and YS's `let` wants
`[name value name value]`. But Clojure allows `name=init` inside a binding
vector, so a Clojure author has no reason to expect it to be rejected, and
because the expression-position question comes up first the message reads as
though position were the problem. It is not: `(let [v 5] v)` works in value
position, inside `fn` bodies, and with multiple body forms.

Suggested:

```
Error: let binding vector must be name/value pairs; `v=5` is not supported (write `v 5`)
```

Context: found while transpiling Clojure to YS. Diagnostic only, but it cost us
a wrong root-cause conclusion — we read the message as "no inline `let` in value
position" and concluded a restructuring was needed, when the fix was one line.

## Draft 3 (optional) — the map one, reframe: our assumption was wrong

**Not filed, deliberately.** This is a record of the mistake rather than a bug
report: flow mappings being unavailable in code mode is documented YS behaviour,
and our emitter emitted a form it had never verified. The notes are kept because
the *error messages* are genuinely unhelpful and a docs clarification would be
welcome:

- `m =: +{a: 1, b: 2}` in code mode reports `mapping values are not allowed
  here` — a YAML scanner error that names neither code mode nor flow mappings as
  the cause, even though the same line is valid in YAML mode. (The YS docs put
  this example in an assignment RHS, which is where we first tried it.)
- `hash-map(a 1 b 2)` reports `Could not resolve symbol: b` (0.2.8) /
  `unable to resolve symbol: b` (0.3.5), which reads like an undefined variable
  rather than "this position wants a string". A hint that bare identifiers in
  `hash-map` are symbol references would turn it into an obvious fix.
- YS maps print in an unspecified order (`{a 1, b 2}` on 0.2.8, `{b 2, a 1}` on
  0.3.5), which makes any exact-output comparison against a printed map
  version-dependent. Worth a sentence in the docs.

If filed, the ask is a docs clarification, not a behaviour change.
