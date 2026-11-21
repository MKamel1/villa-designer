"""Source cards for the L1 checkers: knowledge/eg/*.json -> contracts.SourceCard."""
from __future__ import annotations

import json
from pathlib import Path

from ..contracts import SourceCard

CARD_DIR = Path(__file__).resolve().parents[3] / "knowledge" / "eg"


def load_cards(card_dir: Path | str | None = None) -> dict:
    d = Path(card_dir) if card_dir else CARD_DIR
    cards = {}
    for p in sorted(d.glob("*.json")):
        for c in json.loads(p.read_text(encoding="utf-8"))["cards"]:
            card = SourceCard(**c)
            if card.id in cards:
                raise ValueError("duplicate source card id %s (%s)" % (card.id, p.name))
            cards[card.id] = card
    return cards


def missing_sources(results, cards: dict) -> list:
    """Source ids used by results that have no card (a gate must never cite a card that does not exist)."""
    bad = set()
    for r in results:
        for sid in r.source_ids:
            if sid not in cards:
                bad.add(sid)
    return sorted(bad)
