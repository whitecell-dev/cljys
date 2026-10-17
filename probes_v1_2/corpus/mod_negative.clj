;; Clojure's mod is floored division; rem is truncated. They agree on
;; positive operands and disagree on a negative dividend, so a probe using
;; only positive operands cannot tell the two apart. v1.0.0's P02_arithmetic
;; is exactly that blind case (expected_output ""). Expected values are
;; Clojure's, confirmed against `ys -p -e`: (-7 %% 3) = 2, (-7 % 3) = -1.
;; See compound-packs/yamlscript-semantics/modulo-is-not-remainder.md.
(def a (mod -7 3))
(def b (rem -7 3))
(say a)
(say b)