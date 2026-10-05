(def xs (range 1 5))
(say (str "count=" (count xs)))
(each [x xs] (say x))
