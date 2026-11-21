"""Loaders for knowledge/electrical cards and tables (the only place the engine reads numbers)."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from ..contracts import SourceCard

KDIR = Path(__file__).resolve().parents[3] / "knowledge" / "electrical"


@lru_cache(maxsize=1)
def cards() -> dict[str, SourceCard]:
    raw = json.loads((KDIR / "cards.json").read_text(encoding="utf-8"))
    return {c["id"]: SourceCard(**c) for c in raw}


def card(card_id: str) -> SourceCard:
    return cards()[card_id]


@lru_cache(maxsize=1)
def tables() -> dict:
    return json.loads((KDIR / "tables.json").read_text(encoding="utf-8"))


def table(name: str):
    return tables()[name]


def card_status(card_id: str) -> str:
    return card(card_id).status
