(def nums [1 2 3 4 5])
(def evens (filter (fn [x] (zero? (mod x 2))) nums))
(println evens)
