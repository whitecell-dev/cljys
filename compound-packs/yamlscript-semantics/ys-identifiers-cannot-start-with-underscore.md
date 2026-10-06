---
title: YS identifiers cannot begin with an underscore, so generated names must not
applies_when:
  - adding or changing code that generates a temporary or hoisted binding name
  - debugging YS output rejected with "Invalid symbol"
  - naming a temporary in the emitter
tags: [identifiers, naming, generated-code, compilation]
---

YS reserves a leading underscore. An identifier that starts with `_` is
rejected: `Invalid symbol: '_coll1'`.

This constrains names the emitter *generates* rather than names the author
wrote, which is why it surfaces as a runtime compile error on output nobody
looked at by hand. `_binding_coll` hoists a literal collection into a temporary;
naming that temporary `_coll1` produces a program that will not compile.

Generated identifiers must start with a letter or digit. `coll1` is correct and
is what the emitter uses.

The same caution applies to any future generated name — a placeholder for an
anonymous argument, a synthetic map key, a scratch binding. Check the first
character, not just that the name is unique. Clojure's own `_` wildcard is
likewise not a thing in YS: there is no anonymous binding to emit.