#!/usr/bin/env python3
"""
clj_to_ys.py — Tiny Clojure → YAMLScript transpiler

Handles the subset of Clojure produced by CALYX IR query scripts:
  def, defn, defn-, println/print, fn, filter, map, doseq, take,
  count, seq, get, str, cond, when, if, let, ->, ->>, zero?, not,
  and the destructuring patterns used in IR traversal.

Usage:
  python3 clj_to_ys.py input.clj            # prints YS to stdout
  python3 clj_to_ys.py input.clj -o out.ys  # writes to file
  echo '(println "hi")' | python3 clj_to_ys.py -
"""

import re
import sys
import argparse
from typing import List, Optional, Tuple


# ============================================================================
# LEXER
# ============================================================================


class Token:
    __slots__ = ("kind", "val")

    def __init__(self, kind: str, val: str):
        self.kind = kind
        self.val = val

    def __repr__(self):
        return f"Token({self.kind}, {self.val!r})"


def tokenize(src: str) -> List[Token]:
    tokens = []
    i = 0
    while i < len(src):
        c = src[i]

        # Whitespace
        if c in " \t\n\r,":
            i += 1
            continue

        # Line comment
        if c == ";" and (i == 0 or src[i - 1] != "\\"):
            j = src.find("\n", i)
            tokens.append(Token("COMMENT", src[i : j if j != -1 else len(src)]))
            i = j + 1 if j != -1 else len(src)
            continue

        # Parens / brackets / braces
        if c in "([{":
            tokens.append(Token("OPEN", c))
            i += 1
            continue
        if c in ")]}":
            tokens.append(Token("CLOSE", c))
            i += 1
            continue

        # Quote shorthand
        if c == "'":
            tokens.append(Token("QUOTE", "'"))
            i += 1
            continue

        # Strings
        if c == '"':
            j = i + 1
            while j < len(src) and not (src[j] == '"' and src[j - 1] != "\\"):
                j += 1
            tokens.append(Token("STR", src[i : j + 1]))
            i = j + 1
            continue

        # Keywords
        if c == ":":
            j = i + 1
            while j < len(src) and src[j] not in ' \t\n\r,()[]{}";\\':
                j += 1
            tokens.append(Token("KW", src[i:j]))
            i = j
            continue

        # Regex / dispatch
        if c == "#" and i + 1 < len(src) and src[i + 1] == '"':
            j = i + 2
            while j < len(src) and not (src[j] == '"' and src[j - 1] != "\\"):
                j += 1
            tokens.append(Token("REGEX", src[i : j + 1]))
            i = j + 1
            continue

        # Deref / meta / dispatch
        if c in "@^#":
            tokens.append(Token("DISPATCH", c))
            i += 1
            continue

        # Atoms: numbers, symbols, booleans, nil
        j = i
        while j < len(src) and src[j] not in " \t\n\r,()[]{}\";\\'@^#:":
            j += 1
        if j > i:
            tokens.append(Token("ATOM", src[i:j]))
            i = j
            continue

        i += 1  # skip unknown

    return tokens


# ============================================================================
# PARSER — produces nested Python lists (S-expressions)
# ============================================================================

SExpr = list  # either a list of SExprs or a Token


# Tagged list wrapper so we can distinguish (call) from [vector] from {map}
class SList(list):
    """S-expression list tagged with its opening bracket character."""

    __slots__ = ("bracket",)

    def __init__(self, bracket: str, items):
        super().__init__(items)
        self.bracket = bracket  # '(', '[', or '{'


def is_vec(x) -> bool:
    return isinstance(x, SList) and x.bracket == "["


def is_call(x) -> bool:
    return isinstance(x, SList) and x.bracket == "("


def is_map_literal(x) -> bool:
    return isinstance(x, SList) and x.bracket == "{"


def parse(tokens: List[Token]) -> List[SExpr]:
    tokens = [t for t in tokens if t.kind != "COMMENT"]
    pos = [0]

    def peek() -> Optional[Token]:
        return tokens[pos[0]] if pos[0] < len(tokens) else None

    def consume() -> Token:
        t = tokens[pos[0]]
        pos[0] += 1
        return t

    def read_form() -> SExpr:
        t = peek()
        if t is None:
            return None
        if t.kind == "QUOTE":
            consume()
            inner = read_form()
            return SList("(", [Token("ATOM", "quote"), inner])
        if t.kind == "DISPATCH":
            consume()
            inner = read_form()
            return SList("(", [Token("ATOM", "@"), inner])
        if t.kind == "OPEN":
            bracket = t.val  # '(', '[', or '{'
            consume()
            items = []
            while peek() and peek().kind != "CLOSE":
                items.append(read_form())
            if peek():
                consume()  # eat CLOSE
            return SList(bracket, items)
        return consume()

    forms = []
    while pos[0] < len(tokens):
        f = read_form()
        if f is not None:
            forms.append(f)
    return forms


# ============================================================================
# HELPERS
# ============================================================================


def is_atom(x, val=None) -> bool:
    return isinstance(x, Token) and (val is None or x.val == val)


def atom_val(x) -> str:
    if isinstance(x, Token):
        return x.val
    return str(x)


def is_list(x) -> bool:
    """True for any compound form — call, vector, or map literal."""
    return isinstance(x, SList)


def head_is(x, val: str) -> bool:
    return is_list(x) and x and is_atom(x[0], val)


def is_str_token(x) -> bool:
    return isinstance(x, Token) and x.kind == "STR"


def clj_str_to_ys(s: str) -> str:
    """Convert Clojure double-quoted string to YS form.
    If it contains interpolation markers, keep double-quoted.
    Otherwise prefer single-quoted."""
    inner = s[1:-1]
    # unescape Clojure escapes
    inner = inner.replace('\\"', '"')
    if "$" in inner or "\\" in inner:
        return f'"{inner}"'
    return f"'{inner}'"


# ============================================================================
# DWIM-aware functions (collection can be receiver)
# ============================================================================

DWIM = {
    "filter",
    "map",
    "mapcat",
    "mapv",
    "filterv",
    "keep",
    "remove",
    "take",
    "drop",
    "take-while",
    "drop-while",
    "every?",
    "not-any?",
    "some",
    "sort",
    "sort-by",
    "reduce",
    "partition",
    "interpose",
    "repeat",
    "replace",
    "re-find",
    "re-matches",
    "re-seq",
    "cons",
    "contains?",
    "drop-last",
    "take-last",
    "random-sample",
    "split-at",
    "split-with",
}

# Zero-arg colon-chain functions
ZERO_ARG = {
    "seq",
    "reverse",
    "first",
    "second",
    "last",
    "rest",
    "butlast",
    "count",
    "keys",
    "vals",
    "frequencies",
    "flatten",
    "distinct",
    "shuffle",
    "vec",
    "set",
    "str",
    "lc",
    "uc",
    "trim",
    "words",
    "lines",
}

# Direct renames: Clojure name → YS name
RENAMES = {
    "println": "say",
    "print": "out",
    "prn": "say",
    "zero?": ".!",  # handled specially
    "empty?": ".!",
    "nil?": ".!",
    "not": ".!!",  # handled specially
    "inc": "inc",
    "dec": "dec",
    "mod": "%%",
    "rem": "%",
    "str": None,  # handled specially
    "doseq": "each",
    "dorun": None,
    "doall": None,
    "range": None,  # handled specially → ..
    "slurp": "read",
    "spit": "write",
    "clojure.string/join": "join",
    "clojure.string/split": "split",
    "clojure.string/lower-case": "lc",
    "clojure.string/upper-case": "uc",
    "clojure.string/trim": "trim",
    "json/load": "json/load",
    "json/dump": "json/dump",
}

INFIX_OPS = {
    "+",
    "-",
    "*",
    "/",
    "%",
    "%%",
    "=",
    "not=",
    "<",
    ">",
    "<=",
    ">=",
    "and",
    "or",
    "bit-and",
    "bit-or",
    "bit-xor",
}

OP_MAP = {
    "=": "==",
    "not=": "!=",
    "and": "&&",
    "or": "||",
}


# ============================================================================
# EMITTER
# ============================================================================


class Transpiler:
    def __init__(self):
        self.indent = 0
        self.lines: List[str] = []

    # ---- output helpers ----

    def emit(self, line: str):
        self.lines.append("  " * self.indent + line)

    def emit_raw(self, line: str):
        self.lines.append(line)

    # ---- top-level driver ----

    def transpile(self, forms: List[SExpr]) -> str:
        self.emit_raw("!ys-0")
        self.emit_raw("")
        for form in forms:
            self.emit_top(form)
        return "\n".join(self.lines)

    def emit_top(self, form: SExpr):
        """Emit a top-level form as a YAML mapping pair."""
        if not is_list(form):
            self.emit(self.expr(form))
            return

        head = atom_val(form[0]) if form else ""

        # (def name val)
        if head == "def":
            name = atom_val(form[1])
            val = self.expr(form[2]) if len(form) > 2 else "nil"
            self.emit(f"{name} =: {val}")

        # (defn name [args] body...)  or  (defn- ...)
        elif head in ("defn", "defn-"):
            self._emit_defn(form)

        # (println ...) / (say ...)
        elif head in ("println", "print", "say", "warn", "err"):
            ys_fn = RENAMES.get(head, head)
            args = [self.expr(a) for a in form[1:]]
            if len(args) == 0:
                self.emit(f"{ys_fn}:")
            elif len(args) == 1:
                self.emit(f"{ys_fn}: {args[0]}")
            else:
                self.emit(f"{ys_fn}: {' '.join(args)}")

        # (doseq [[k v] coll] body...) — original Clojure form
        elif head == "doseq":
            self._emit_doseq(form)

        # (each [x coll] body...) — canonical normalized form
        elif head == "each":
            self._emit_each(form)

        # (let [bindings...] body...)
        elif head == "let":
            self._emit_let(form)

        # (when test body...)
        elif head == "when":
            self._emit_when(form)

        # (if test then else?)
        elif head == "if":
            self._emit_if(form)

        # (-> x ...) / (->> x ...)
        elif head in ("->", "->>"):
            self.emit(self.expr(form))

        # (do body...)
        elif head == "do":
            for sub in form[1:]:
                self.emit_top(sub)

        # generic call as statement
        else:
            self.emit(self.expr(form))

    # ---- defn ----

    def _emit_defn(self, form: SExpr):
        priv = "-" if atom_val(form[0]) == "defn-" else ""
        name = atom_val(form[1])
        args = form[2]  # vector of params
        body = form[3:]

        params = self._emit_params(args)
        self.emit(f"defn{priv} {name}({params}):")
        self.indent += 1
        for b in body:
            self.emit_top(b)
        self.indent -= 1
        self.emit_raw("")

    def _emit_params(self, args) -> str:
        """Convert [arg1 arg2 & rest] or destructured args to YS param string."""
        if not is_list(args):
            return ""
        parts = []
        i = 0
        while i < len(args):
            a = args[i]
            if is_atom(a, "&"):
                i += 1
                parts.append(f"& {atom_val(args[i])}")
            elif is_vec(a):
                # destructuring: [[k v]]
                inner = " ".join(atom_val(x) for x in a if isinstance(x, Token))
                parts.append(f"[{inner}]")
            else:
                parts.append(atom_val(a))
            i += 1
        return " ".join(parts)

    # ---- doseq ----

    def _emit_doseq(self, form: SExpr):
        # (doseq [binding coll, ...] body...)
        bindings = form[1]
        body = form[2:]

        # Parse binding pairs: [[k v] coll] or [x coll]
        bind_pairs = []
        i = 0
        while i < len(bindings) - 1:
            pat = bindings[i]
            coll = bindings[i + 1]
            bind_pairs.append((pat, coll))
            i += 2

        if len(bind_pairs) == 1:
            pat, coll = bind_pairs[0]
            pat_s = self._pattern(pat)
            coll_s = self.expr(coll)
            self.emit(f"each {pat_s} {coll_s}:")
        else:
            # nested each
            first_pat, first_coll = bind_pairs[0]
            self.emit(f"each {self._pattern(first_pat)} {self.expr(first_coll)}:")
            self.indent += 1
            for pat, coll in bind_pairs[1:]:
                self.emit(f"each {self._pattern(pat)} {self.expr(coll)}:")
                self.indent += 1

        self.indent += 1
        for b in body:
            self.emit_top(b)
        self.indent -= 1
        # close extra indents for multi-binding
        for _ in bind_pairs[1:]:
            self.indent -= 1

    # ---- each (canonical normalized form) ----

    def _emit_each(self, form: SExpr):
        """Emit (each [binding coll] body...) — canonical post-normalization form.
        The binding vector is form[1]: [pattern collection].
        Works for both:
          (each [x numbers] ...)           — simple binding
          (each [kv active-relations] ...)  — normalized from doseq destructuring
        """
        binding = form[1]  # a [pat coll] vector
        body = form[2:]

        # binding[0] = pattern, binding[1] = collection
        pat = binding[0] if len(binding) > 0 else Token("ATOM", "_")
        coll = binding[1] if len(binding) > 1 else Token("ATOM", "nil")

        pat_s = self._pattern(pat)
        coll_s = self.expr(coll)
        self.emit(f"each {pat_s} {coll_s}:")
        self.indent += 1
        for b in body:
            self.emit_top(b)
        self.indent -= 1

    def _pattern(self, pat) -> str:
        if is_vec(pat):
            inner = " ".join(atom_val(x) for x in pat if isinstance(x, Token))
            return f"[{inner}]"
        return atom_val(pat)

    # ---- let ----

    def _emit_let(self, form: SExpr):
        bindings = form[1]
        body = form[2:]
        i = 0
        while i < len(bindings) - 1:
            name = atom_val(bindings[i])
            val = self.expr(bindings[i + 1])
            self.emit(f"{name} =: {val}")
            i += 2
        for b in body:
            self.emit_top(b)

    # ---- if / when ----

    def _emit_if(self, form: SExpr):
        test = self.expr(form[1])
        then_ = form[2] if len(form) > 2 else None
        else_ = form[3] if len(form) > 3 else None
        self.emit(f"if {test}:")
        self.indent += 1
        if then_:
            self.emit_top(then_)
        if else_:
            self.indent -= 1
            self.emit("else:")
            self.indent += 1
            self.emit_top(else_)
        self.indent -= 1

    def _emit_when(self, form: SExpr):
        test = self.expr(form[1])
        self.emit(f"when {test}:")
        self.indent += 1
        for b in form[2:]:
            self.emit_top(b)
        self.indent -= 1

    # ---- expression emitter ----

    def expr(self, form) -> str:
        if form is None:
            return "nil"

        # Bare token
        if isinstance(form, Token):
            return self._token_expr(form)

        # Not a tagged SList at all
        if not is_list(form):
            return "nil"

        # Empty form
        if not form:
            return "nil"

        # ---- Vector literal [1 2 3] → +[1 2 3] ----
        if is_vec(form):
            items = " ".join(self.expr(x) for x in form)
            return f"+[{items}]"

        # ---- Map literal {k v ...} → +{k: v, ...} ----
        if is_map_literal(form):
            if not form:
                return "+{}"
            pairs = []
            it = iter(form)
            for k in it:
                v = next(it, None)
                ks = self.expr(k)
                vs = self.expr(v) if v is not None else "nil"
                pairs.append(f"{ks}: {vs}")
            return "+{" + ", ".join(pairs) + "}"

        # Everything below is a call form: (head arg arg ...)
        head = form[0]
        hv = atom_val(head) if isinstance(head, Token) else ""

        # (quote x) → 'x (rare in this domain)
        if hv == "quote":
            return f"'{self.expr(form[1])}'"

        # (zero? x) → x.!
        if hv in ("zero?", "empty?", "nil?"):
            return f"{self.expr(form[1])}.!"

        # (not x) → x.!!
        if hv == "not":
            return f"{self.expr(form[1])}.!!"

        # (count x) → x.#
        if hv == "count":
            return f"{self.expr(form[1])}.#"

        # (seq x) → x.seq (zero-arg colon chain)
        if hv == "seq":
            return f"{self.expr(form[1])}:seq"

        # (first/last/rest/keys/vals/reverse x)
        if hv in ZERO_ARG and len(form) == 2:
            return f"{self.expr(form[1])}:{hv}"

        # (get m k) → m.'k' or m.k or nth(m n) for integer/variable keys
        if hv == "get":
            obj = self.expr(form[1])
            key = form[2]
            ks = atom_val(key) if isinstance(key, Token) else self.expr(key)
            if is_str_token(key):
                inner = key.val[1:-1]
                return f"{obj}.'{inner}'"
            if isinstance(key, Token) and key.kind == "KW":
                return f"{obj}.{ks.lstrip(':')}"
            # Integer literal → nth(obj n)
            if isinstance(key, Token) and re.match(r"^\d+$", key.val):
                return f"nth({obj} {key.val})"
            # Variable symbol → nth(obj var) since property lookup is static
            if isinstance(key, Token) and key.kind == "ATOM":
                return f"nth({obj} {key.val})"
            return f"nth({obj} {self.expr(key)})"

        # (str ...) → concatenation or interpolation
        if hv == "str":
            return self._emit_str(form[1:])

        # (println/say ...)
        if hv in ("println", "print", "say", "warn"):
            ys = RENAMES.get(hv, hv)
            args = [self.expr(a) for a in form[1:]]
            return f"{ys}({' '.join(args)})"

        # (fn [args] body) or (fn [[k v]] body)
        if hv == "fn":
            return self._emit_fn(form)

        # (-> x f g ...)  threading
        if hv == "->":
            return self._thread(form[1:], forward=True)

        # (->> x f g ...)
        if hv == "->>":
            return self._thread(form[1:], forward=False)

        # (range start end) → start .. end
        if hv == "range":
            if len(form) == 3:
                return f"({self.expr(form[1])} .. {self.expr(form[2])})"
            if len(form) == 2:
                return f"(0 .. {self.expr(form[1])})"
            return "0 .. 99"

        # (take n coll) / (drop n coll) — DWIM
        if hv in DWIM:
            return self._dwim_call(hv, form[1:])

        # (filter fn coll) — DWIM
        if hv == "filter":
            return self._dwim_call("filter", form[1:])

        # Infix operators
        if hv in INFIX_OPS or hv in OP_MAP:
            return self._infix(hv, form[1:])

        # (cond test expr ... :else expr)
        if hv == "cond":
            return self._inline_cond(form[1:])

        # (if test then else) — inline
        if hv == "if":
            test = self.expr(form[1])
            then_ = self.expr(form[2]) if len(form) > 2 else "nil"
            else_ = self.expr(form[3]) if len(form) > 3 else "nil"
            return f"{test}.if({then_} {else_})"

        # (when test expr) — inline
        if hv == "when":
            test = self.expr(form[1])
            val = self.expr(form[2]) if len(form) > 2 else "nil"
            return f"{test}.when({val})"

        # (let [...] expr) — inline (single-expr body only)
        if hv == "let" and len(form) == 3:
            # emit as block would be cleaner but inline for nested use
            bindings = form[1]
            body = form[2]
            parts = []
            i = 0
            while i < len(bindings) - 1:
                n = atom_val(bindings[i])
                v = self.expr(bindings[i + 1])
                parts.append(f"{n}={v}")
                i += 2
            return f"(let [{' '.join(parts)}] {self.expr(body)})"

        # (apply f coll)
        if hv == "apply":
            f = self.expr(form[1])
            coll = self.expr(form[2]) if len(form) > 2 else "_"
            return f"{coll}.(f*)"

        # (map-indexed f coll)
        if hv == "map-indexed":
            f = self.expr(form[1])
            coll = self.expr(form[2]) if len(form) > 2 else "_"
            return f"{coll}.map-indexed({f} _)"

        # (into [] coll) / (into {} coll)
        if hv == "into":
            target = self.expr(form[1])
            coll = self.expr(form[2]) if len(form) > 2 else "_"
            return f"{coll}:vec" if "[]" in target else f"{coll}:set"

        # Generic function call → fn(arg1 arg2 ...)
        fn_name = RENAMES.get(hv, hv)
        if fn_name is None:
            fn_name = hv
        args = [self.expr(a) for a in form[1:]]
        if not args:
            return f"{fn_name}:"
        return f"{fn_name}({' '.join(args)})"

    # ---- token emitter ----

    def _token_expr(self, t: Token) -> str:
        if t.kind == "STR":
            return clj_str_to_ys(t.val)
        if t.kind == "KW":
            # :else → else, :key → 'key' in data contexts
            kv = t.val.lstrip(":")
            return kv
        if t.kind == "ATOM":
            v = t.val
            if v == "true":
                return "true"
            if v == "false":
                return "false"
            if v == "nil":
                return "nil"
            # rename
            return RENAMES.get(v, v)
        if t.kind == "REGEX":
            return t.val  # pass through #"..." unchanged
        return t.val

    # ---- fn ----

    def _emit_fn(self, form: SExpr) -> str:
        """Convert (fn [args] body) to lambda or fn([args] body)."""
        args = form[1]  # should be a vec [...]
        body = form[2] if len(form) > 2 else None

        # Destructured single arg: (fn [[k v]] body)
        if is_vec(args) and len(args) == 1 and is_vec(args[0]):
            inner = " ".join(atom_val(x) for x in args[0] if isinstance(x, Token))
            body_s = self.expr(body) if body else "nil"
            return f"fn([{inner}] {body_s})"

        # Single plain-symbol arg — safe to use _ shorthand
        if (
            is_vec(args)
            and len(args) == 1
            and isinstance(args[0], Token)
            and body is not None
        ):
            param = atom_val(args[0])
            body_s = self.expr(body)
            body_ys = re.sub(rf"\b{re.escape(param)}\b", "_", body_s)
            return f"\\({body_ys})"

        # Multi-arg → fn([a b] body)
        params = " ".join(
            atom_val(a) if isinstance(a, Token) else self._pattern(a)
            for a in args
            if isinstance(a, (Token, SList))
        )
        body_s = self.expr(body) if body else "nil"
        return f"fn([{params}] {body_s})"

    # ---- str ----

    def _emit_str(self, parts: List[SExpr]) -> str:
        """Convert (str a b c) to YS string concatenation."""
        if not parts:
            return "''"
        # All literal strings → single interpolated string
        segments = []
        for p in parts:
            if is_str_token(p):
                segments.append(p.val[1:-1].replace('"', "'"))
            elif isinstance(p, Token):
                segments.append(f"${atom_val(p)}")
            elif is_list(p):
                segments.append(f"$({self.expr(p)})")
            else:
                segments.append(str(p))
        return '"' + "".join(segments) + '"'

    # ---- threading macros ----

    def _thread(self, forms: List[SExpr], forward: bool) -> str:
        """(-> x (f a) g) → x.f(a).g  or  x.g.f(a) for ->>"""
        result = self.expr(forms[0])
        for step in forms[1:]:
            if isinstance(step, Token):
                # bare function name
                fn = RENAMES.get(atom_val(step), atom_val(step))
                if fn in ZERO_ARG:
                    result = f"{result}:{fn}"
                else:
                    result = f"{result}.{fn}"
            elif is_list(step):
                fn = RENAMES.get(atom_val(step[0]), atom_val(step[0]))
                args = [self.expr(a) for a in step[1:]]
                if fn in ZERO_ARG and not args:
                    result = f"{result}:{fn}"
                elif args:
                    result = f"{result}.{fn}({' '.join(args)})"
                else:
                    result = f"{result}.{fn}"
        return result

    # ---- DWIM calls ----

    def _dwim_call(self, fn: str, args: List[SExpr]) -> str:
        """Emit DWIM-aware call: coll.fn(f) when coll is last arg."""
        fn_ys = RENAMES.get(fn, fn)
        if len(args) == 1:
            return f"{self.expr(args[0])}:{fn_ys}"
        if len(args) == 2:
            pred = self.expr(args[0])
            coll = self.expr(args[1])
            return f"{coll}.{fn_ys}({pred})"
        # 3+ args: fn(arg1 arg2 ... coll)
        head_args = [self.expr(a) for a in args[:-1]]
        coll = self.expr(args[-1])
        return f"{coll}.{fn_ys}({' '.join(head_args)})"

    # ---- infix ----

    def _infix(self, op: str, args: List[SExpr]) -> str:
        ys_op = OP_MAP.get(op, op)
        if len(args) == 1:
            return f"{ys_op}({self.expr(args[0])})"
        parts = [self.expr(a) for a in args]
        return f" {ys_op} ".join(parts)

    # ---- inline cond ----

    def _inline_cond(self, clauses: List[SExpr]) -> str:
        """Emit cond as nested .if() chain (inline) — only for simple cases."""
        if not clauses:
            return "nil"
        test = clauses[0]
        val = clauses[1] if len(clauses) > 1 else Token("ATOM", "nil")
        rest = clauses[2:]
        tv = atom_val(test) if isinstance(test, Token) else ""
        if tv in ("else", ":else") or (
            isinstance(test, Token) and test.kind == "KW" and test.val == ":else"
        ):
            return self.expr(val)
        test_s = self.expr(test)
        val_s = self.expr(val)
        rest_s = self._inline_cond(rest)
        return f"{test_s}.if({val_s} {rest_s})"


# ============================================================================
# BLOCK-FORM EMITTER for cond at statement level
# ============================================================================


def rewrite_top_cond(transpiler: Transpiler, form: SExpr):
    """Emit (cond ...) as block-form YS cond."""
    clauses = form[1:]
    transpiler.emit("cond:")
    transpiler.indent += 1
    i = 0
    while i < len(clauses) - 1:
        test = clauses[i]
        val = clauses[i + 1]
        tv = atom_val(test) if isinstance(test, Token) else ""
        if tv in ("else", ":else") or (isinstance(test, Token) and test.kind == "KW"):
            transpiler.emit(f"else: {transpiler.expr(val)}")
        else:
            transpiler.emit(f"{transpiler.expr(test)}: {transpiler.expr(val)}")
        i += 2
    transpiler.indent -= 1


# ============================================================================
# PATCH: wire block-cond into emit_top
# ============================================================================

_orig_emit_top = Transpiler.emit_top


def _patched_emit_top(self, form):
    if is_list(form) and form and is_atom(form[0], "cond"):
        rewrite_top_cond(self, form)
    else:
        _orig_emit_top(self, form)


Transpiler.emit_top = _patched_emit_top


# ============================================================================
# CLI
# ============================================================================


def transpile_source(src: str) -> str:
    tokens = tokenize(src)
    forms = parse(tokens)
    t = Transpiler()
    return t.transpile(forms)


def main():
    p = argparse.ArgumentParser(description="Clojure → YAMLScript transpiler")
    p.add_argument("input", help="Input .clj file or - for stdin")
    p.add_argument("-o", "--output", default=None, help="Output .ys file")
    args = p.parse_args()

    if args.input == "-":
        src = sys.stdin.read()
    else:
        with open(args.input) as f:
            src = f.read()

    result = transpile_source(src)

    if args.output:
        with open(args.output, "w") as f:
            f.write(result)
        print(f"Written to {args.output}")
    else:
        print(result)


if __name__ == "__main__":
    main()
