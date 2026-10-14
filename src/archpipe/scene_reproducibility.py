"""Deterministic runtime inputs and translation-safe solid arithmetic.

Coordinates are metres; signed volume is cubic metres, positive for outward
winding. SHA-256 is the stable 256-bit digest used to bind authored inputs.
"""
import hashlib
import json
import math


def stable_seed(authored):
    """Bind a seed to the complete authored record, independent of hash salt.

    Sorted JSON (JavaScript Object Notation) preserves array order, ignores
    dictionary insertion order and refuses non-finite authored numbers.
    """
    raw = json.dumps(authored, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')
    return int.from_bytes(hashlib.sha256(raw).digest(), 'big')


def signed_volume(faces):
    """Triangulate polygon fans in double precision around one local origin.

    Subtract before multiplication, on authored Python floats rather than
    already rounded Blender vectors. A common origin is essential: a separate
    origin for each face would erase its tetrahedral contribution.
    """
    if not faces:
        return 0.0
    origin = tuple(map(float, faces[0][0]))
    def terms():
        for face in faces:
            pts = [tuple(float(p[i])-origin[i] for i in range(3)) for p in face]
            a = pts[0]
            for index in range(1, len(pts)-1):
                b, c = pts[index], pts[index+1]
                cross = (b[1]*c[2]-b[2]*c[1], b[2]*c[0]-b[0]*c[2], b[0]*c[1]-b[1]*c[0])
                yield (a[0]*cross[0]+a[1]*cross[1]+a[2]*cross[2])/6.0
    return math.fsum(terms())


def require_outward(faces, ident):
    """Refuse inverted/zero-volume closed solids; never repair design winding."""
    volume = signed_volume(faces)
    if not math.isfinite(volume) or abs(volume) <= 1e-10:
        raise ValueError(ident+': zero or non-finite enclosed volume')
    if volume < 0:
        raise ValueError(ident+': inward-facing solid (negative signed volume)')
    return volume


def compare_receipts(before, after):
    """Fail closed on missing or changed evaluated geometry bindings."""
    findings = []
    for key in ('schema', 'authored_scene_sha256', 'evaluated_meshes_sha256', 'curtains'):
        if key not in before or key not in after or before[key] != after[key]:
            findings.append('missing or changed '+key)
    if before.get('schema') != 'evaluated-scene/1' or after.get('schema') != 'evaluated-scene/1':
        findings.append('unsupported evaluated scene receipt')
    for record in (before, after):
        curtains = record.get('curtains')
        if not isinstance(curtains, dict) or any(not r.get('mesh_sha256') for r in curtains.values()):
            findings.append('unbound evaluated curtain mesh')
    return findings


def randomness_findings(source, label='source'):
    """Audit Python calls for process hashes and entropy-backed random defaults.

    Resolves import aliases, including NumPy random modules. Explicitly seeded
    generator instance methods are allowed; global random-module sampling is
    refused. This examines source, never comments/docstrings or output text.
    """
    import ast
    tree = ast.parse(source.lstrip('\ufeff'))
    aliases = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for item in node.names:
                aliases[item.asname or item.name.split('.')[0]] = item.name if item.asname else item.name.split('.')[0]
        elif isinstance(node, ast.ImportFrom):
            for item in node.names:
                aliases[item.asname or item.name] = (node.module or '')+'.'+item.name
    def name(node):
        if isinstance(node, ast.Name): return aliases.get(node.id, node.id)
        if isinstance(node, ast.Attribute): return name(node.value)+'.'+node.attr
        return ''
    constructors = {'random.Random', 'random.seed', 'numpy.random.default_rng', 'numpy.random.RandomState', 'numpy.random.seed'}
    findings = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call): continue
        called = name(node.func)
        reason = None
        if called in ('hash', 'builtins.hash'):
            reason = 'process-random built-in hash'
        elif called in constructors:
            supplied = node.args[0] if node.args else next((k.value for k in node.keywords if k.arg in ('seed','a')), None)
            if supplied is None or (isinstance(supplied, ast.Constant) and supplied.value is None):
                reason = 'unseeded random generator'
        elif called.startswith(('random.', 'numpy.random.')) and called not in constructors:
            reason = 'global random sampling without an owned seeded generator'
        if reason: findings.append(f'{label}:{node.lineno}: {reason}')
    return findings


def repository_randomness_findings(root=None):
    from pathlib import Path
    root = Path(root) if root else Path(__file__).resolve().parents[2]
    return [finding for folder in ('src', 'scripts') for path in sorted((root/folder).rglob('*.py'))
            for finding in randomness_findings(path.read_text(encoding='utf-8'), str(path.relative_to(root)))]
