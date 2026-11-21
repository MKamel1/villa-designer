"""The canonical design model of the villa: one placed-object record (`contracts.DesignElement`) per element.

    from archpipe.model import load
    elements = load("D1")          # list[DesignElement]; see docs/lanes/L2-model.md

Exporter: `python -m archpipe.model.export [--snapshot]`.
"""
from .api import counts, export, generate, load, load_json, schema_version  # noqa: F401
from .schema import validate  # noqa: F401
