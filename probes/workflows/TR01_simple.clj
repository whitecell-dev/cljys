(def ir (json/load (read "calyx_mcp_v6.json")))
(say "=== SCANNING FOR DEPENDENTS ===")
(def r-map (get ir "R"))
(say (str "Found " (count r-map) " modules"))
