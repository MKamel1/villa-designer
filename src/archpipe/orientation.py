"""Client side names and true solar rotation have separate recorded purposes.

Directions are strings '-x', '+x', '-y', '+y' in model coordinates.
Azimuth is degrees clockwise from true north; altitude is degrees above horizon.
"""
import json
import math
from pathlib import Path

RECORD = Path(__file__).resolve().parents[2] / 'knowledge/site-orientation.json'


def record():
    return json.loads(RECORD.read_text(encoding='utf-8'))


def side_name(direction):
    return record()['naming_convention']['sides'][direction]


def zone_name(direction):
    return record()['zone_names'][side_name(direction)]


def sun_direction(azimuth_deg, altitude_deg):
    angle = math.radians(azimuth_deg-record()['true_north']['model_y_bearing_deg'])
    altitude = math.radians(altitude_deg)
    return (math.sin(angle)*math.cos(altitude), math.cos(angle)*math.cos(altitude), math.sin(altitude))


def historical_aliases(value):
    """Explicitly migrate a frozen legacy landscape payload without rewriting evidence.

    Only recorded identifiers and the landscape's legacy bed/route keys change.
    Call on landscape payloads, never on a true-north solar record.
    """
    data = record()
    aliases = data['legacy_aliases']
    zones = data['legacy_zone_aliases']
    extra = data['legacy_fragment_aliases']
    def change(item):
        if isinstance(item,dict):return {change(k):change(v) for k,v in item.items()}
        if isinstance(item,(list,tuple)):return type(item)(change(v) for v in item)
        if isinstance(item,str):return aliases.get(item,extra.get(item,zones.get(item,item)))
        return item
    return change(value)


def appearance_seed(identifier):
    """Keep a renamed climber's established deterministic appearance."""
    reverse={new:old for old,new in record()['legacy_aliases'].items()}
    return sum(map(ord,reverse.get(identifier,identifier)))
