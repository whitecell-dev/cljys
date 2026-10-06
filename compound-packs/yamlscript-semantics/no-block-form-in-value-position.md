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