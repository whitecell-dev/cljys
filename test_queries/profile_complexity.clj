(def ir (json/load (read "calyx_mcp_v6.json")))

(println "=== PROFILING MODULE STRUCTURAL COMPLEXITY ===")
(def modules (get ir "M"))

;; Filter out null/empty modules and map them to [module_id, key_count] pairs
(def module-sizes
  (filter
    (fn [m]
      (let [p (get m "Profile")]
        (not (nil? p))))
    modules))

(println (str "Total active structural profiles scanned: " (count module-sizes)))

;; Take the top 3 modules and print their internal footprint
(each [m (take 3 module-sizes)]
  (let [profile-name (get m "Profile")
        layer-count (count m)]
    (println (str "Module Name: " profile-name " -> Internal Keys: " layer-count))))
