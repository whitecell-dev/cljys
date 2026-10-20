;; v1.4.0 — Clojure does not interpolate. A literal `$HOME` must stay literal;
;; emitting it into a YS double-quoted string instead makes YS look up HOME.
;; The second line also carries an escape, which forces a double-quoted YS
;; string, so the literal dollar has to survive that path too.
(println "cost is $5 and $HOME")
(println "path\n$HOME")
