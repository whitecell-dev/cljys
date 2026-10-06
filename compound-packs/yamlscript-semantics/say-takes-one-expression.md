---
title: say and out take one expression, so multi-argument print calls must be str-wrapped
applies_when:
  - adding or changing println, print, prn, say, or out emission
  - writing a probe whose expected output is printed text
  - debugging YS output where a print call prints the wrong thing
tags: [io, print, arity, str, canonical-form]
---

`println`, `print`, and `prn` map to YS `say`, `out`, and `say`. These take a
**single expression**. Clojure's variadic form does not survive the mapping.

```
(println a b c)              ✗  variadic
(println (str a " " b))      ✓  one expression
```

So a multi-argument print becomes a `str` concatenation wrapped in one call:

```
say: str(a " " b " " c)
```

This is stated in `README.md`'s canonical Clojure specification as an
LLM front-end responsibility — the normalizer is supposed to produce the
single-argument form. The emitter must not paper over a miss by emitting
`say: a b c`: that is neither valid YS nor a faithful translation, and the
failure is silent rather than loud.

Zero arguments is legal and means the bare keyword form (`say:`), with no value.

Related: `str` with a nil argument renders differently between runtimes. A
probe that prints through `str` must pin the expected output by running it, not
by reasoning about what Clojure would print — this is a case where the two
runtimes genuinely differ and `resources/form-mapping.md` does not settle it.