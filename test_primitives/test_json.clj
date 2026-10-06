(def data (json/load (slurp "data.json")))
(def output-data {"status" "ok" "count" 42})
(def output (json/dump output-data))
