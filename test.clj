(def ir (json/load (read "calyx_mcp_v6.json")))

(println "=== RE-EVALUATING RELATIONS (R) ===")
(def r-map (get ir "R"))

;; Filter out empty maps to find active protocol nodes
(def active-relations
  (->> r-map
       (filter (fn [kv] (seq (second kv))))))

(println (str "Total active protocol relational nodes found: " (count active-relations)))

(println "\n=== RESOLVING BITWISE ROLE-BITS FROM MODULES ===")
(def modules (get ir "M"))

;; Module 49 is FastMCP. Use nth for vector index access in Clojure too.
(def module-49 (nth modules 49))
(println (str "Module 49 Profile: " module-49))

;; Print the active nodes exactly as jq saw them
(doseq [kv (take 5 active-relations)]
  (let [k (first kv)
        v (second kv)]
    (println (str "Module ID: " k " -> Actions: " (get v "0")))))
