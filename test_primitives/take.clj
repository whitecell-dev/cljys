(def xs [10 20 30 40 50])
(each [x (take 3 xs)]
  (println x))
