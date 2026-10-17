;; v1.3.0 — `let` in VALUE position: the minimal, independent witness for the
;; two `let` defects. TR01_workflow covers the same path inside a realistic
;; query shape; this one is small enough to read as the specification.
;;
;; Statement position is a DIFFERENT emitter path: `_emit_let` renders bindings
;; as `k =: v` and emits no `let` at all, so a statement-position repro would
;; pass without touching either defect. Confirmed by transpiling both forms.
;;
;; 1. binding form — Clojure's `name=init` is legal Clojure and rejected by YS
;;    ("let requires an even number of forms in binding vector")
;; 2. infix body — unparenthesized, YS evaluates the body as its LAST OPERAND:
;;    `(let [n 3] n + 1)` is 1, not 4. A silent wrong value, not an error, which
;;    is why it needs a probe rather than a manual check.
(def plain (let [x 1] x))
(def summed (let [x 1 y 2] (+ x y)))
(def nested (let [n 3] (let [m 4] (+ n m))))
(say plain)
(say summed)
(say nested)
