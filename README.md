# clj-to-yamlscript-transpiler

##Why this matters
Leverage LLMs for what they're actually good at: This toolchain uses LLMs to drastically reduce the amount of code you need to write when adapting deterministic systems for extreme expressiveness in syntax or natural language. Instead of hand-writing parsers and normalization passes, you use the LLM as an intent-preserving front-end and let deterministic tooling handle the rest.

A hybrid compilation toolchain that transpiles a subset of *Clojure* data queries into *YAMLScript (YS)*, which then compiles to ultra-fast, zero-dependency native binaries using GraalVM/SCI.

This project solves the "expressivity gap" between Clojure's vocabulary and rigid syntax transpilers by using a dual-pass architecture: an LLM as a structural, intent-preserving front-end normalizer, followed by a 100% deterministic local Python emitter pass.

## Architecture & Pipeline

Parsing every edge case of an expressive Lisp with a simple local parser leads to complexity. This project splits the work by matching tools to their strengths:

1. *The Semantic Front-End (LLM):* Takes idiomatic Clojure and normalizes it into a strict, flat canonical intermediate representation. No destructuring, explicit `(str)` wrapping.
2. *The Emitter Middle-End (Python):* A rigid, deterministic tokenizer and parser that maps the canonical Clojure AST directly onto YAMLScript structural forms.
3. *The Native Back-End (YAMLScript):* Compiles the clean `.ys` script into a native, standalone binary using `ys -c`.
[Expressive Clojure Query]
    |
    v  (LLM Normalization Pass: flattens destructuring & prints)
[Canonical Clojure Subset]
    |
    v  (clj_to_ys.py: Local Deterministic AST Map)
[Valid YAMLScript Code]
    |
    v  (ys -c compilation)
[Native Executable Binary]
## Quick Start

### 1. Normalize & Transpile
Feed your expressive Clojure query into the normalization pipeline, then pass it to the Python emitter:
python3 clj_to_ys.py input.clj -o output.ys
### 2. Compile to Native Binary
Turn the resulting YAMLScript code into a standalone native binary that executes in milliseconds with zero JVM boot overhead:
ys -c output.ys
## The Canonical Clojure Specification

To ensure deterministic compilation without syntax errors or broken scalar mappings in YAMLScript, the incoming Clojure must conform to this strict subset. This is handled automatically by the LLM front-end prompt.

### 1. No Parameter Destructuring
Complex sequence destructuring like `(fn [[k v]] ...)` or `(doseq [[k v] ...])` is forbidden. Bind the collection element to a single variable and extract items explicitly using `first`, `second`, or `nth` inside a `let` block:
;; Good / Canonical
(doseq [kv (take 5 active-relations)]
  (let [k (first kv)
        v (second kv)]
    (println (str "Module ID: " k))))
### 2. Single-Argument Explicit Print Concatenation
`println` or `print` statements cannot accept multiple variadic arguments. They must accept exactly one argument. Wrap multi-variable strings completely inside an explicit `(str ...)` form:
;; Good / Canonical
(println (str "Total nodes found: " (count active-relations)))
### 3. Explicit Vector Index Lookups
Sequence indexing must use the `(nth vector index)` format rather than calling the vector or index as an implicit function form:
;; Good / Canonical
(def module-49 (nth modules 49))
## Components

- `clj_to_ys.py`: The core tokenizer, S-expression parser, and code emitter written in Python. It maps native atoms, infix operators, threading macros (`->`, `->>`), `let` blocks, and `doseq` structures to YAMLScript layouts.

## License

This toolchain is open-source and licensed under the MIT License.
