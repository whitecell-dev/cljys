;; v1.3.0 — a keyword-key map literal, pinned through a VALUE.
;;
;; Pins the quoted-key emission in the map-literal branch: `{:a 1}` renders its
;; key through expr(), which strips the colon, so an unquoted key makes YS
;; resolve `a` as a symbol and fail. The error wording differs between ys
;; releases, so this asserts the value, never the message.
(def m {:a 1})
(say (get m :a))
