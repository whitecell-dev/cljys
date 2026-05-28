(def ir (json/load (read "calyx_mcp_v6.json")))

(println "=== SCANNING FOR DEPENDENTS OF ACTIONS NODE: '0' ===")
(def r-map (get ir "R"))

;; Find all modules whose action map contains key "0"
(def targeting-nodes
  (filter (fn [kv]
            (let [v (second kv)]
              (seq (get v "0"))))
          r-map))

(println (str "Found " (count targeting-nodes) " modules explicitly tracking target context."))

(doseq [kv (take 3 targeting-nodes)]
  (let [module-id (first kv)]
    (println (str " -> Dependency Match: Module " module-id " -> Intersects Node '0'"))))
