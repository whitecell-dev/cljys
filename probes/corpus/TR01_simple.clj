;; FAILURE FIXTURE — not a regression probe. No manifest entry names this file.
;;
;; This is the richer form of the query shape. It uses `let` inside a call
;; argument (line 8) and inside an `each` body (line 12), so it transpiles
;; cleanly and then fails at runtime:
;;     Error: let requires an even number of forms in binding vector
;; That is the emitter defect at clj-to-ys.py:825-842, the same one that makes
;; the wired probe TR01_workflow ERROR.
;;
;; It is kept, not wired, because the wired probes/workflows/TR01_simple.clj is
;; a 4-line simplification that drops both `let` uses entirely and therefore
;; passes. Wiring this file in would add a permanent ERROR to CI rather than a
;; regression signal. Retained as a named, discoverable reproduction of the
;; defect - see README.md "Known to Break".
;;
;; Distinguish it from the two other kinds of probe artifact in this repo:
;;   regression suite  - probes/manifest.json entries, expected to pass
;;   failure fixtures  - this file; reproduce a known defect, expected to fail
;;   historical record - convergence-claims/evidence*/, immutable

(def ir (json/load (read "calyx_mcp_v6.json")))
(say "=== SCANNING FOR DEPENDENTS ===")
(def r-map (get ir "R"))
(def targeting-nodes
  (filter
   (fn [kv] 
     (let [v (second kv)] 
       (get v "0")))
   r-map))
(say (str "Found " (count targeting-nodes) " modules"))
(each [kv (take 3 targeting-nodes)]
  (let [module-id (first kv)]
    (say (str " -> Module " module-id))))
