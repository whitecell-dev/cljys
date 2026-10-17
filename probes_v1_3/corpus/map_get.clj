;; v1.3.0 — a two-key map, read back by key rather than printed.
;;
;; YS maps are unordered: `say` of this map prints `{a 1, b 2}` on ys 0.2.8 and
;; `{b 2, a 1}` on 0.3.5. An exact-output probe over the printed map would
;; therefore be a version-fragile test of nothing, so this pins the key
;; rendering through lookups, where key order cannot appear.
(def m {:a 1 :b 2})
(say (get m "a"))
(say (get m :b))
