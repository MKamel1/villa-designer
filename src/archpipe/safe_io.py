"""Typed portable bridge values and atomic output publication.

An image viewer or the search indexer holding the previous file makes a
plain overwrite fail with OSError 22 (seen twice: halfway through a render
batch, and at the end of a 20-minute pipeline run when out/bedroom.png was
open). Write beside the target, then swap it in, retrying the sharing lock.
The fix first lived only in the render driver, so the pipeline runner hit
the same error. Migrated outputs share this boundary; remaining siblings
and native-runtime proof limits are listed in docs/serialization-boundary.md.
"""
import json
import os
import uuid
import time
from contextlib import contextmanager
from collections import namedtuple

try:
    text_type = unicode
    integer_types = (int, long)
except NameError:
    text_type = str
    integer_types = (int,)

Byte = namedtuple('Byte', 'value')
Color = namedtuple('Color', 'red green blue')
ElementId = namedtuple('ElementId', 'value')
XYZ = namedtuple('XYZ', 'x y z unit')  # coordinates with explicit length unit
Quantity = namedtuple('Quantity', 'value unit')
Text = namedtuple('Text', 'original normalized')
_RECORDS = dict((t.__name__, t) for t in (Byte, Color, ElementId, XYZ, Quantity, Text))


def normalized_text(value):
    """CR/LF to logical LF lines; remove terminal line endings, retain original."""
    return Text(value, value.replace('\r\n', '\n').replace('\r', '\n').rstrip('\n'))


def convert_length(quantity, unit):
    """Convert an explicitly unit-tagged length; feet are exactly 304.8 mm."""
    encode(quantity)
    scales = {'ft': 304.8, 'mm': 1.0, 'm': 1000.0}
    if not isinstance(quantity, Quantity) or unit not in scales:
        raise ValueError('conversion requires a Quantity and known length unit')
    return Quantity(quantity.value * scales[quantity.unit] / scales[unit], unit)


def encode(value):
    """Portable tagged records; never stringify an unsupported foreign value."""
    name = type(value).__name__
    if name in _RECORDS and isinstance(value, tuple):
        if isinstance(value, (Byte, Color)):
            if any(type(c) not in integer_types or not 0 <= c <= 255 for c in value):
                raise ValueError('invalid byte channel')
        if isinstance(value, ElementId) and type(value.value) not in integer_types:
            raise ValueError('identifier must be an exact integer')
        if isinstance(value, (XYZ, Quantity)):
            if value.unit not in ('ft', 'mm', 'm'):
                raise ValueError('unknown length unit')
            for number in value[:-1]:
                if isinstance(number, bool) or not isinstance(number, integer_types + (float,)):
                    raise ValueError('length must be numeric')
        if isinstance(value, Text) and value != normalized_text(value.original):
            raise ValueError('text normalization disagrees with original')
        return {'type': name, 'value': [encode(v) for v in value]}
    if name == 'Byte':
        return encode(Byte(int(value)))
    if name == 'Color':
        return encode(Color(int(value.Red), int(value.Green), int(value.Blue)))
    if name == 'ElementId':
        return encode(ElementId(int(value.Value if hasattr(value, 'Value') else value.IntegerValue)))
    if name == 'XYZ':
        return encode(XYZ(float(value.X), float(value.Y), float(value.Z), 'ft'))
    if value is None:
        tag = 'null'
    elif isinstance(value, bool):
        tag = 'bool'
    elif isinstance(value, integer_types):
        tag = 'int'
    elif isinstance(value, float):
        if value != value or value in (float('inf'), float('-inf')):
            raise ValueError('non-finite number')
        tag = 'float'
    elif isinstance(value, bytes) and not isinstance(value, text_type):
        return {'type': 'bytes', 'value': list(bytearray(value))}
    elif isinstance(value, (str, text_type)):
        tag = 'str'
    elif isinstance(value, dict):
        return {'type': 'dict', 'value': [[encode(k), encode(v)] for k, v in value.items()]}
    elif isinstance(value, (list, tuple)):
        return {'type': 'tuple' if isinstance(value, tuple) else 'list', 'value': [encode(v) for v in value]}
    else:
        raise TypeError('unsupported boundary type: ' + name)
    return {'type': tag, 'value': value}


def decode(data):
    tag, value = data['type'], data['value']
    if tag in _RECORDS:
        result = _RECORDS[tag](*(decode(v) for v in value))
    elif tag == 'dict':
        result = dict((decode(k), decode(v)) for k, v in value)
    elif tag in ('list', 'tuple'):
        result = [decode(v) for v in value]
        if tag == 'tuple':
            result = tuple(result)
    elif tag == 'bytes':
        result = bytes(bytearray(value))
    elif tag in ('null', 'bool', 'int', 'float', 'str'):
        result = value
    else:
        raise ValueError('unknown boundary type: ' + tag)
    if encode(result) != data:
        raise ValueError('invalid typed value')
    return result


def assert_round_trip(value, serializer=None):
    """Also compare tags because Python equality treats False as zero."""
    encoded = encode(value)
    restored = decode(json.loads((serializer or json.dumps)(encoded)))
    if encode(restored) != encoded:
        raise AssertionError('boundary round trip changed type or value')
    return restored


def assert_measured_readback(actual, measured, sources):
    """Independent measured witness and model provenance for every field.

    The witness must come from a separate measurement, never a copy of actual.
    Equality with the specification alone cannot establish provenance.
    """
    if set(actual) != set(measured) or set(actual) != set(sources):
        raise ValueError('read-back lacks independent witnesses')
    for field in actual:
        if sources[field] != 'model' or encode(actual[field]) != encode(measured[field]):
            raise ValueError('read-back is not measured: ' + field)


@contextmanager
def atomic_path(path, attempts=10, wait_s=1.0):
    """Unique same-directory staging, fsync, replace; never delete destination.

    Python 2 uses .NET File.Replace, as os.replace is unavailable there.
    """
    path = path if isinstance(path, (str, text_type)) else str(path)
    tmp = path + '.' + uuid.uuid4().hex + '.part'
    if attempts < 1:
        raise ValueError('attempts must be positive')
    try:
        yield tmp
        with open(tmp, 'r+b') as stream:
            stream.flush()
            os.fsync(stream.fileno())
        for i in range(attempts):
            try:
                if hasattr(os, 'replace'):
                    os.replace(tmp, path)
                else:
                    from System.IO import File
                    if File.Exists(path):
                        File.Replace(tmp, path, None)
                    else:
                        File.Move(tmp, path)
                return
            except OSError:
                if i == attempts - 1:
                    raise
                time.sleep(wait_s)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def save_bytes(path, data, attempts=10, wait_s=1.0):
    with atomic_path(path, attempts, wait_s) as tmp:
        with open(tmp, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())


def copy_file(src, dst, **kw):
    with open(str(src), 'rb') as stream:
        save_bytes(dst, stream.read(), **kw)


def save_text(path, text, **kw):
    save_bytes(path, text.encode('utf-8'), **kw)


def save_json(path, data, serializer=None, **kw):
    payload = (serializer or json.dumps)(data, ensure_ascii=True, allow_nan=False, **kw)
    save_text(path, payload + '\n')


def load_json(path):
    with open(str(path), 'rb') as stream:
        raw = stream.read()
    encoding = 'utf-16' if raw.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8-sig'
    return json.loads(raw.decode(encoding))


def writable_path(path):
    """`path`, or `<stem>-v2<suffix>`, `-v3` ... when the file exists and cannot be opened for writing (a PDF open
    in the user's viewer on Windows): the newest output is never lost to a lock, and the locked file is untouched."""
    from pathlib import Path
    path = Path(path)
    n, cand = 1, path
    while True:
        try:
            if cand.exists():
                with open(cand, "r+b"):
                    pass
            return cand
        except PermissionError:
            n += 1
            cand = path.with_name("%s-v%d%s" % (path.stem, n, path.suffix))
