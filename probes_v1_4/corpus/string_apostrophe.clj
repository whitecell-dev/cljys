;; v1.4.0 — a single quote inside a Clojure string must be doubled in a YS
;; single-quoted string; emitting it raw ends the scalar early.
(println "it's fine")
