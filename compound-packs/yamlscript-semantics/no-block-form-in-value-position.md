---
title: A block form cannot appear in value position; hoist it to a =: assignment first
applies_when:
  - adding or changing how if, when, cond, each, or defn is emitted
  - producing an expression that embeds a loop, branch, or function definition
  - debugging YS output that fails to compile or evaluates to the wrong thing
tags: [block-form, hoisting, structure, compilation]
---

Some YS forms are statements. They cannot be used where a value is expected, so
emitting one inline produces output that either fails to compile or silently
evaluates to something other than the intended value.

Block forms (cannot appear in argument/value position):

- `each` — a loop
- `defn`, `defn-` — a function definition
- block `if` — `if` with `then`/`else` on their own lines
- `cond`, block `when`, `doseq`

Scalar forms (fine in value position): literals, symbols, infix expressions,
non-block calls, inline `x.if(y z)`, inline `x.when(y)`, property access
`obj.key`, zero-arg colon chains `xs:keys`, the count operator `xs.#`.

**`let` is a scalar form — with two YS-specific constraints.** It belongs in the
list above, not with the block forms: `(let [x 1] x)` is legal in value
position, inside a `fn` body, and with multiple body forms, on ys 0.2.8 and
0.3.5 alike. What it rejects is the *shape*, not the position:

1. **Binding vectors take name/value pairs, not Clojure's `name=init`.**
   `(let [x=1] x)` is legal Clojure and fails in YS with "let requires an even
   number of forms in binding vector" — `[x=1]` is one form. Emit `[x 1]`.
2. **Wrap an infix body in parentheses.** `(let [n 3] n + 1)` evaluates to `1`,
   not `4`: YS returns the body's last operand. `(let [n 3] (n + 1))` is `4` on
   both releases. This one is silent — a wrong value, not an error — so it needs
   a probe rather than a manual check, and it is why the emitter parenthesizes
   only an infix body: a bare `(n)` would be a call of `n`, which is not
   callable.

Both are pinned by probe `let_value_pos` (suite v1.3.0) and by mutation, and
`TR01_workflow` covers the same path in a realistic query shape. Statement
position is a different emitter path entirely (`_emit_let` renders `k =: v` and
emits no `let`), so a statement-position repro proves nothing about either.

When a new form family is added, decide explicitly: block or scalar? If it can
appear in either position, emit the block form to a hoisted assignment and keep
a scalar form for value position, as `if` does.

Hoist to a `=:` assignment before use:

```
# wrong: a block form in value position
total =: count(filter(each x xs: x.ok))
say: total

# right: the loop is hoisted, the scalar stays inline
matches =: each x xs:
  if x.ok:
    x
total =: count(matches)
```

The emitter already threads this via `_pending` / `_flush_pending`: a
binding-collection render can queue a hoisted line that must land *before* the
statement that needed it, and in the correct scope. Two latent defects lived in
that hoist (`git log`: `d9755e4`, `b64dc11`) — nested-loop ordering is where a
scope mistake hides, because the wrong scope still compiles and still runs.

When a new form family is added, decide explicitly: block or scalar? If it can
appear in either position, emit the block form to a hoisted assignment and keep
a scalar form for value position, as `if` does.
## Corrections

- **2026-10-17.** This rule is where the belief that "`let` is a block form"
  ended up. It never said so — but `clj-to-ys.py`'s KNOWN marker claimed "YS
  rejects inline `let` in value position, so any call argument containing a let
  breaks", and `REPORT.md` described the fix as needing statement/expression
  separation in the emitter. Both were wrong, and this rule is the corrected
  home for the fact: `let` is scalar, its binding vector takes name/value pairs
  instead of Clojure's `name=init`, and an infix body must be parenthesized.
  Verified on ys 0.2.8 and 0.3.5 (`docs/clojure-vs-ys-gotchas.md`); pinned by
  probe `let_value_pos` and by two mutations. The scalar list above is the
  substantive edit; the rest of this rule is unchanged.
