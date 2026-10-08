"""Value-keyed, build-local memoization for derived villa records.

Callers receive independent copies because scene and review passes may annotate records.
The cache cannot survive a build or an exception, and a changed input has a new key.
"""
from __future__ import annotations

import contextvars
import copy
import json
from contextlib import contextmanager

_cache = contextvars.ContextVar("villa_build_cache", default=None)


@contextmanager
def scope():
    token = _cache.set({})
    try:
        yield
    finally:
        _cache.reset(token)


def derived(name, inputs, compute):
    cache = _cache.get()
    if cache is None:
        return compute()
    key = (name, json.dumps(inputs, sort_keys=True, separators=(",", ":")))
    if key not in cache:
        cache[key] = copy.deepcopy(compute())
    return copy.deepcopy(cache[key])


def immutable(name, inputs, compute):
    """Reuse an immutable result by its complete hashable input value.

    Unlike derived records, tuples of validation errors need no copy. The
    caller must supply an immutable key and return an immutable result.
    """
    cache = _cache.get()
    if cache is None:
        return compute()
    key = (name, inputs)
    if key not in cache:
        cache[key] = compute()
    return cache[key]
