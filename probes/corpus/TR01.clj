(def ir (json/load (read "calyx_mcp_v6.json")))

(say "=== SCANNING FOR DEPENDENTS OF ACTIONS NODE: '0' ===")
(def r-map (get ir "R"))

(def targeting-nodes
  (filter
   (fn [kv] 
     (let [v (second kv)] 
       (get v "0")))
   r-map))

(say
 (str
  "Found "
  (count targeting-nodes)
  " modules explicitly tracking target context."))

(each
 [kv (take 3 targeting-nodes)]
 (let [module-id (first kv)]
   (say
    (str
     " -> Dependency Match: Module "
     module-id
     " -> Intersects Node '0'"))))
