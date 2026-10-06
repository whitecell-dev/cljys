---
title: An each binding is exactly two forms, and a literal collection must be hoisted or ranged
applies_when:
  - adding or changing doseq, each, or any loop-construct emission
  - normalizing destructuring in a loop binding
  - debugging a loop that YS rejects or iterates the wrong number of times
tags: [each, doseq, loop, binding, destructuring, hoisting]
---

A YS `each` binding vector holds exactly **two** forms — the loop variable and
the collection:

```
each [var coll]:
  body
```

**No destructuring.** YS cannot destructure a sequence element into a pair.
Normalize by binding the element to one name and extracting explicitly:

```
(doseq [[k v] m] ...)              ✗
(each [kv m] let k =: (first kv)   ✓
       let v =: (second kv)
       ...)
```

Same rule for `fn` parameters — `(fn [[k v]] ...)` is not supported; bind one
name and extract inside the body.

**A collection literal cannot be the binding collection.** Emitting
`each x +[1 2]:` fails at runtime, not at compile time: YS reads the bracketed
group as part of the binding vector rather than as the collection, and reports
"for requires an even number of forms in binding vector". Only two forms are
accepted in that position — a variable (`each x xs:`) or a range expression
(`each x (1 .. 2):`).

So `_binding_coll` has exactly two legal moves for a literal:

- a **contiguous** run of integers becomes `(first .. last)` — inclusive here,
  which is correct because contiguity makes inclusive-last equal to Clojure's
  exclusive stop;
- **anything else is hoisted** into a `=:` assignment emitted immediately before
  the `each` line, and the binding references that name.

Never silently turn a non-contiguous vector like `[1 5 3]` into a range — that
changes the data. Hoist it.

Watch the scope of the hoist: the assignment must be emitted at the enclosing
statement level, not inside the loop body. `d9755e4` and `b64dc11` were both
defects in exactly this ordering.