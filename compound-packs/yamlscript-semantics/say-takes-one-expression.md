---
title: say accepts space-separated expressions, but not adjacent string literals
applies_when:
  - adding or changing println, print, prn, say, or out emission
  - writing a probe whose expected output is printed text
  - debugging YS output where a print call prints the wrong thing
tags: [io, print, arity, str, canonical-form]
---

`println`, `print`, and `prn` map to YS `say`, `out`, and `say`. YS accepts a
space-separated expression list, so a numeric variadic call survives:

```
say: 1 2 3                   ✓  prints "1 2 3"
say: 'a' 'b'                 ✗  compile error: expected <block end>
say: str('a' ' ' 'b')        ✓  prints "a b"
```

The restriction is YAML scalar parsing, not `say` arity: two quoted scalars on
one line are a parse error, and `str()` mangles lists and maps (it prints
`clojure.core$_PLUS_@...`), so `str()` is not a general replacement.

`clj-to-ys.py` emits the space-separated form. That works for numbers but fails
loudly for multiple string literals; see `KNOWN_ISSUES.md`. Zero arguments is
legal and means the bare keyword form (`say:`).

Related: `str` with a nil argument renders differently between runtimes. A
probe that prints through `str` must pin the expected output by running it, not
by reasoning about what Clojure would print — this is a case where the two
runtimes genuinely differ and `resources/form-mapping.md` does not settle it.
