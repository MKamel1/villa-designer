"""The product library for every category beyond luminaires.

Two kinds of record, kept apart on purpose:

    product     something that can be bought: manufacturer, SKU or range,
                dimensions, performance. Design decisions and schedules name
                products (a primary and an alternate), as luminaires do.
    appearance  something that can be rendered: a PBR material or a 3D model
                with its real-world size. Free libraries (Poly Haven,
                ambientCG) supply these.

A link between them carries a labelled claim (schema.CLAIMS):
manufacturer-supplied, scan-of-product or look-alike-proxy. A render shows
the claim, so a free marble texture never passes silently as a named
product (the faithful-render rule).

Two layers, like the luminaire library: the catalogue index (everything a
source lists, unverified) and verified items, whose files passed every
computable check. Each check is recorded as passed, failed or
not_checkable. A check with no published data to test against is
not_checkable, and never counts as a pass.

The luminaire library (archpipe.luminaires) stays as it is; lighting.py
exposes its verified rows as products through a read-only adapter.
"""
