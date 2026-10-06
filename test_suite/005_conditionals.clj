(defn sign [x]
  (cond (< x 0) -1 (> x 0) 1 :else 0))