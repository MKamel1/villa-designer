"""Retain physical component intent while batching by render material.

Names here are authored builder component names, not object identifiers or
room labels. Unknown components retain the assembly kind and still face the
normal proxy/solid screen.
"""

KINDS = {
    'screen': 'tv-panel', 'oven-glass': 'appliance-front',
    'microwave-glass': 'appliance-front', 'glass-door': 'glass-pane',
    'glass': 'glass-pane', 'cable-tray': 'joinery-cable-tray',
    'wet-floor': 'finish-layer', 'tray': 'finish-layer',
    'flush-plate': 'wall-plate', 'pull': 'joinery-pull',
    'front': 'door-leaf', 'drawer': 'door-leaf',
    'sliding-door-pocketed': 'door-leaf', 'joinery_end_panel': 'wall-panel',
    'back': 'cabinet-carcass', 'side': 'cabinet-carcass',
    'base': 'cabinet-carcass', 'carcass': 'cabinet-carcass',
    'shelf': 'shelf', 'top': 'worktop', 'worktop': 'worktop',
    'bikes-hooks': 'wall-plate',
}

# The legacy source calls the authored end panel a generic block. That role
# is only physical for this assembly; unknown blocks keep their proxy screen.
ASSEMBLY_COMPONENT_KINDS = {('joinery_end_panel', 'block'): 'wall-panel'}
JOINERY_ASSEMBLIES = frozenset(('base_run', 'island', 'tall_column', 'wardrobe',
    'sideboard', 'bedside_table', 'bookcase', 'daybed_nook', 'pantry_shelving',
    'store_shelving', 'under_stair_storage', 'folding_counter', 'window_bench',
    'tv_unit', 'joinery_end_panel'))
BOARD_NAMES = frozenset(('back', 'side', 'base', 'carcass'))


def assembly_kind(member):
    """Support use belongs to the assembly, independently of board type."""
    return member.get('assembly_kind', member.get('part_kind'))


def component_kind(assembly, names, *, fallback=None):
    declared = []
    for name in names:
        # These prefixes are authored storage module uses. Their suffix
        # still describes the physical board, irrespective of stored content.
        suffix = name.rsplit('-', 1)[-1]
        kind = ASSEMBLY_COMPONENT_KINDS.get((assembly, name), KINDS.get(name))
        if name in BOARD_NAMES and assembly not in JOINERY_ASSEMBLIES:
            kind = None  # A padded chair back is not a cabinet board.
        if kind is None and assembly in JOINERY_ASSEMBLIES and suffix in ('back', 'side', 'base', 'shelf'):
            kind = KINDS[suffix]
        declared.append(kind or fallback or assembly)
    return declared[0] if declared and len(set(declared)) == 1 else fallback or assembly
