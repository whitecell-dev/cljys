!ys-0
# YAMLSCRIPT KNOWLEDGE BASE v1.1
# CALYX-style bundle for LLM consumption

metadata:
  version: "1.1.0"
  target: "YAMLScript"
  purpose: "Complete semantic understanding for code generation and transpilation"
  note: "This is a constrained IR for LLM→compiler communication, not documentation"

# ============================================================================
# FORM CLASSIFICATION (Critical for emitter)
# ============================================================================

form_classes:
  scalar:
    description: "Can appear in argument/value position"
    includes:
      - literals (strings, numbers, booleans, nil)
      - symbols
      - infix expressions
      - function calls (non-block)
      - inline if: "x.if(y z)"
      - inline when: "x.when(y)"
      - property access: "obj.key"
      - zero-arg colon chain: "xs:keys"
      - count operator: "xs.#"

  block:
    description: "Cannot appear in argument position"
    includes:
      - each
      - defn, defn-
      - let (statement form with multiple assignments)
      - block if (with then/else on separate lines)
      - cond
      - when (block form)
      - doseq

  rule: "Block forms MUST be extracted to =: assignment before use in value position"

# ============================================================================
# GRAMMAR (Canonical forms only)
# ============================================================================

grammar:
  def: "name =: value"
  defn: "defn name(args):\n  body"
  defn-: "defn- name(args):\n  body"

  # Canonical each — binding MUST be 2-element vector
  each: "each [var coll]:\n  body"

  if:
    block: "if test:\n  then-body\nelse:\n  else-body"
    inline: "test.if(then-val else-val)"

  when:
    block: "when test:\n  body"
    inline: "test.when(val)"

  cond: "cond:\n  test1: expr1\n  test2: expr2\n  else: expr3"

  let: "name =: value"  # sequential assignments, no nested let
  fn: "fn([args] body)"

  io:
    say: "say: expr"      # single expression only
    say_expr: "say(expr)" # inline form
    warn: "warn: expr"
    err: "err: expr"

  # Clojure (range a b) is EXCLUSIVE of b; YS (a .. b) is INCLUSIVE.
  # Emit the function form, which is exclusive like Clojure's.
  # 1-arg (range n) -> range(0,n); 3-arg (range a b s) -> range(a,b,s).
  range: "range(start, end[, step])"
  nth: "nth(coll idx)"
  join: "join(sep coll)"
  split: "split(regex s)"

# ============================================================================
# OPERATORS (With arity)
# ============================================================================

operators:
  infix:
    binary:   # Exactly 2 arguments
      - name: "%"
        ys: "%"
        clojure: "rem"
      - name: "%%"
        ys: "%%"
        clojure: "mod"
      - name: "=="
        ys: "=="
        clojure: "="
      - name: "!="
        ys: "!="
        clojure: "not="
      - name: "<"
        ys: "<"
        clojure: "<"
      - name: ">"
        ys: ">"
        clojure: ">"
      - name: "<="
        ys: "<="
        clojure: "<="
      - name: ">="
        ys: ">="
        clojure: ">="
      - name: "&&"
        ys: "&&"
        clojure: "and"
      - name: "||"
        ys: "||"
        clojure: "or"

    variadic:  # 2+ arguments joined by operator
      - "+"
      - "-"
      - "*"
      - "/"

  prefix:
    not: ".!!"
    zero?: ".!"
    empty?: ".!"
    nil?: ".!"

  clojure_mapping:
    "zero?": ".!"
    "empty?": ".!"
    "nil?": ".!"
    "not": ".!!"
    "=": "=="
    "not=": "!="
    "and": "&&"
    "or": "||"
    "rem": "%"
    "mod": "%%"

# ============================================================================
# MAP LITERAL CONSTRAINTS
# ============================================================================

map_literal:
  syntax: 'hash-map("key" value "key2" value2)'
  allowed_positions:
    - assignment_rhs: 'm =: hash-map("a" 1 "b" 2)'
    - function_arguments: 'f(hash-map("a" 1))'
    - nested_expressions: true
  rule: "Use hash-map(); +{...} is rejected by YS in code mode"

# ============================================================================
# VECTOR LITERAL
# ============================================================================

vector_literal:
  syntax: "+[item1 item2 item3]"
  rule: "No commas. No implicit calls. Use nth() for access."

# ============================================================================
# STRING RULES
# ============================================================================

strings:
  default: "'single-quoted'"
  interpolation: "\"double-quoted with $var or $(expr)\""
  multiline_literal: "|\n  line1\n  line2"
  multiline_folded: ">\n  folded line1\n  folded line2"
  rule: "Prefer single quotes unless interpolation or escapes required"

# ============================================================================
# DWIM (Don't Worry, It's Magic)
# ============================================================================

dwim:
  collection_as_receiver:
    - "coll.filter(pred)"
    - "coll.map(fn)"
    - "coll.take(n)"
    - "coll.drop(n)"
    - "coll.reduce(fn init)"

  zero_arg_colon_chain:
    - "xs:keys"
    - "xs:vals"
    - "xs:seq"
    - "xs:first"
    - "xs:last"
    - "xs:rest"
    - "xs:reverse"
    - "xs:distinct"
    - "xs:shuffle"
    - "xs:flatten"

  count_operator: "xs.#"

# ============================================================================
# SEMANTICS
# ============================================================================

semantics:
  execution_model: "Compiles to Clojure → runs on SCI → GraalVM native image"
  determinism: "transpiler only; runtime determinism unverified"
  sandboxed: "unverified"
  no_dynamic_code_loading: true
  no_macros: true
  no_jvm_startup: true

# ============================================================================
# CANONICAL FORMS
# ============================================================================

canonical_forms:
  threading:
    clojure: "(-> xs (map inc) (filter even?))"
    ys: "xs.map(inc).filter(even?)"

  destructuring_removal:
    clojure: "(doseq [[k v] xs] (println k v))"
    ys: "each [kv xs]\n  let k =: (first kv)\n  let v =: (second kv)\n  say: str(k v)"

  string_interpolation:
    clojure: "(str \"x=\" x)"
    ys: "\"x=$x\""

  map_literal:
    clojure: "{:a 1 :b 2}"
    ys: 'hash-map("a" 1 "b" 2)'

  vector_literal:
    clojure: "[1 2 3]"
    ys: "+[1 2 3]"

  multi_arg_println:
    clojure: "(println a b c)"
    ys: "say: a b c"  # unquoted expressions; adjacent string literals fail

# ============================================================================
# FORBIDDEN PATTERNS
# ============================================================================

forbidden_patterns:
  - description: "Destructuring in each binding"
    pattern: "each [[k v] coll]"
    canonical: "each [kv coll]\n  let k =: (first kv)\n  let v =: (second kv)"

  - description: "Destructuring in fn args"
    pattern: "(fn [[k v]] ...)"
    canonical: "(fn [kv] (let [k (first kv) v (second kv)] ...))"

  - description: "Multi-arg println with adjacent string literals"
    pattern: "(println \"a\" \"b\")"
    canonical: "say: str('a' ' ' 'b')"

  - description: "Implicit vector call"
    pattern: "(xs 0)"
    canonical: "(nth xs 0)"

  - description: "Inline each body"
    pattern: "each x coll: say: x"
    canonical: "each [x coll]:\n  say: x"

  - description: "Nested threading with ambiguous arity"
    pattern: "->> xs map inc filter even?"
    canonical: "xs.map(inc).filter(even?)"

  - description: "Multi-arity functions"
    pattern: "(defn foo ([x] ...) ([x y] ...))"
    note: "Use default args instead: (defn foo (x y 0) ...)"

  - description: "Namespace-qualified symbols"
    pattern: "clojure.string/join"
    note: "Use unqualified builtins: join"

  - description: "Macros"
    pattern: "defmacro"
    note: "YAMLScript has no macros"

  - description: "Dynamic vars"
    pattern: "def ^:dynamic"
    note: "Not supported in SCI"

  - description: "Reader macros"
    pattern: "#()"
    canonical: "(fn [x] ...)"

# ============================================================================
# BUILT-INS
# ============================================================================

builtins:
  io:
    - say
    - out
    - warn
    - err

  string:
    - join
    - split
    - lc
    - uc
    - trim
    - words
    - lines

  collection:
    - range
    - nth
    - inc
    - dec
    - shuffle
    - distinct
    - flatten
    - vec
    - set

  json:
    - json/load
    - json/dump

  predicate:
    - zero?
    - empty?
    - nil?
    - not
