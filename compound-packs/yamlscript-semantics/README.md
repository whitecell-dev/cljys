# yamlscript-semantics

Prescriptive equivalence rules for mapping Clojure onto YAMLScript (YS) in this
repo's transpiler, `clj-to-ys.py`.

Clojure and YS are both Clojure-shaped, which is exactly the trap: syntax that
compiles in both can still mean different things. Every rule here describes a
case where the two disagree and the emitter must bridge it. A rule exists
because the bug class is real — `REPORT.md` section 10 records the range bug,
where `(a .. b)` is inclusive in YS and `(range a b)` is exclusive in Clojure,
and four probes caught it only after the fact.

`resources/form-mapping.md` holds the full form-by-form table. It is storage:
referenced from the rules below, never read as a rule itself.

## Rules

| Rule | Guards |
|---|---|
| `range-end-is-exclusive.md` | iteration bounds, the bug that started this pack |
| `modulo-is-not-remainder.md` | `mod` vs `rem`, sign of the result |
| `no-block-form-in-value-position.md` | `each`/`defn`/`cond`/block-`if` hoisting |
| `collection-literals-need-plus-prefix.md` | `+[...]`, `+{...}`, no implicit call |
| `each-binding-is-two-forms.md` | binding shape and collection-literal hoisting |
| `ys-identifiers-cannot-start-with-underscore.md` | generated binding names |
| `say-takes-one-expression.md` | `println`/`print` arity |
| `no-macros-dynamic-vars-or-reader-macros.md` | the SCI runtime's actual capabilities |

## Adding a rule

One file per rule, top level, with `title` and `applies_when` frontmatter —
required, or the resolver skips the file. `applies_when` is matched
semantically against the work being planned or reviewed, so write the situation
the way a request would phrase it ("adding support for `cond`"), not a topic
label. Keep rules disjoint: when two rules reach the same line, review reports
both contradictions and cannot pick a winner.

A rule earns its place by a divergence someone has hit or could plausibly hit.
If it only restates what YS's own docs say, it is a `resources/` entry instead.