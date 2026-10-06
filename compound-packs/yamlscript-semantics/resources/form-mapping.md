# Storage — never read as a rule

Referenced from the rules one level up. Nothing here is discovered as a rule:
no `title`/`applies_when` frontmatter, and it lives below the pack's top level
by design.

## Form-by-form mapping

Derived from `spec.md` (metadata version 1.1.0), which remains the canonical
reference. This file exists so a rule can point at the whole table without a
pack file becoming a second copy of the spec that can drift from it.

### Definitions

| Clojure | YS |
|---|---|
| `(def name val)` | `name =: val` |
| `(defn name [args] body)` | `defn name(args):` + body |
| `(defn- name [args] body)` | `defn- name(args):` + body |
| `(let [k v ...] body)` | sequential `k =: v` assignments, no nested `let` |
| `(fn [args] body)` | `fn([args] body)` |

### Control flow

| Clojure | YS | Class |
|---|---|---|
| `(each [x coll] body)` | `each [x coll]:` + body | block |
| `(doseq [x coll] body)` | `each [x coll]:` + body | block |
| `(if t a b)` | block: `if t:` / `a` / `else:` / `b`; inline: `t.if(a b)` | both |
| `(when t body)` | block: `when t:` / body; inline: `t.when(a)` | both |
| `(cond ...)` | `cond:` with `test: expr` clauses and `else:` | block |

### Functions and access

| Clojure | YS |
|---|---|
| `(nth coll i)` | `nth(coll, i)` |
| `(count xs)` | `xs.#` |
| `xs:keys` / `:vals` / `:first` / `:rest` / `:reverse` / `:distinct` | zero-arg colon chain on the collection |
| `coll.filter(f)` / `.map(f)` / `.take(n)` / `.drop(n)` | collection as receiver |
| `(-> xs (map inc) (filter even?))` | `xs.map(inc).filter(even?)` |
| `(range 1 4)` | `range(1, 4)` — see `range-end-is-exclusive.md` |
| `(mod x y)` / `(rem x y)` | `x %% y` / `x % y` — see `modulo-is-not-remainder.md` |

### Operators

Binary, exactly two arguments: `%` (rem), `%%` (mod), `==` (=), `!=` (not=),
`<`, `>`, `<=`, `>=`, `&&` (and), `||` (or).

Variadic, two or more joined by the operator: `+`, `-`, `*`, `/`.

Prefix: `not` → `.!!`; `zero?`, `empty?`, `nil?` → `.!`.

### Literals

| Clojure | YS |
|---|---|
| `[1 2 3]` | `+[1 2 3]` (no commas) |
| `{:a 1 :b 2}` | `+{a: 1, b: 2}` (commas separate pairs) |
| `"text"` | `'text'` (single quotes preferred) |
| `"x=$x"` | `"x=$x"` (double quotes for interpolation or escapes) |
| multi-line | `\|` literal or `>` folded block |

### IO

`println` → `say`, `print` → `out`, `prn` → `say`, `warn` → `warn`, `err` → `err`.
All take a single expression — see `say-takes-one-expression.md`.

## Verification

The rules here describe intent; `probes/` is what proves it. Each rule's
divergence should have at least one probe, and that probe should include the
case the rule exists for — the negative operand for `modulo-is-not-remainder.md`,
the nested composition for `range-end-is-exclusive.md`.

To check YS behavior directly rather than reasoning about it:

```bash
ys -p -e 'expression'
```