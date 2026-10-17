;; clj-to-ys.py _binding_coll: a literal vector cannot sit in an `each`
;; binding position, so a contiguous ascending run of integer literals becomes
;; a YS range and anything else is hoisted into a temp binding. Both branches
;; are here; no probe covered this emitter branch before v1.2.0.
(doseq [x [1 2 3]]
  (say x))

(doseq [y [1 5 3]]
  (say y))