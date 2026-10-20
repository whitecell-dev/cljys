#!/usr/bin/env python3
"""Generate comprehensive test suite for clj-to-ys.py"""

import os

TESTS = {
    "001_basic_assignment": """
(def x 42)
(def y "hello")
(def z [1 2 3])
""",
    "002_arithmetic": """
(def a (+ 1 2))
(def b (* 2 3 4))
(def c (mod 7 3))
(def d (rem 7 3))
""",
    "003_comparisons": """
(def a (= 1 2))
(def b (not= 1 2))
(def c (< 1 2))
(def d (> 2 1))
""",
    "004_predicates": """
(def a (zero? 0))
(def b (not true))
(def c (nil? nil))
""",
    "005_conditionals": """
(defn sign [x]
  (cond (< x 0) -1 (> x 0) 1 :else 0))
""",
    "006_loops_each": """
(each [x [1 2 3]] (println x))
""",
    "007_loops_nested": """
(doseq [x [1 2] y [3 4]] (println x y))
""",
    "008_collections_map": """
(def result (map inc [1 2 3]))
""",
    "009_collections_filter": """
(def result (filter even? [1 2 3 4]))
""",
    "010_collections_reduce": """
(def result (reduce + 0 [1 2 3]))
""",
    "011_strings": """
(def name "Alice")
(def greeting (str "Hello, " name))
(def upper (clojure.string/upper-case name))
""",
    "012_threading": """
(def result (-> [1 2 3] (map inc) (filter even?)))
""",
    "013_json": """
(def data (json/load "{\\\"a\\\":1}"))
""",
    "014_maps": """
(def m {:a 1 :b 2})
""",
    "015_functions": """
(defn add [a b] (+ a b))
(defn greet [name] (str "Hello " name))
""",
}


def main():
    os.makedirs("test_suite", exist_ok=True)
    for name, code in TESTS.items():
        with open(f"test_suite/{name}.clj", "w") as f:
            f.write(code.strip())
    print(f"Generated {len(TESTS)} test files in test_suite/")


if __name__ == "__main__":
    main()
