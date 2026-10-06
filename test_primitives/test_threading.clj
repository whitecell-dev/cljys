;; test_threading.clj
(def result (-> [1 2 3 4 5] (map inc) (filter even?) (reduce +)))
