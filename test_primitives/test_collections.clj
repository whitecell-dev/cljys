;; test_collections.clj
(def nums [1 2 3 4 5])
(def squares (map (fn [x] (* x x)) nums))
(def evens (filter (fn [x] (zero? (mod x 2))) nums))
(def sum (reduce + 0 nums))
