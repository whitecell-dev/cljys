;; v1.4.0 — println with several args is a single `say:` with expressions
;; separated by spaces. Pinned for numbers; see KNOWN_ISSUES.md for the
;; string-literal case, which YS rejects at compile time rather than
;; printing the wrong thing.
(println 1 2 3)
