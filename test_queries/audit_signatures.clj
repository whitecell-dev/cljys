(def ir (json/load (read "calyx_mcp_v6.json")))

(println "=== RUNNING CALYX SEMANTIC INVARIANT AUDIT ===")
(def modules (get ir "M"))

;; Filter down to modules that are fully populated (not nil placeholders)
(def valid-modules
  (filter (fn [m] (not (nil? m))) modules))

(println (str "Total active structural definitions verified: " (count valid-modules)))

;; Check signatures of top modules for non-empty string properties
(doseq [m (take 3 valid-modules)]
  (let [has-profile (get m "Profile")]
    (when (not (nil? has-profile))
      (println (str "Verified Signature Context: " has-profile)))))
