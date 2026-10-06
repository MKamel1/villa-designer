"""External claims ingestion, content sniffing, provenance tracking, and integrity guards.

This module provides defenses against trusting unverified external claims (servers,
files, catalogues, download folders, search engines, BIM families):
- Sniff content by raw bytes (magic numbers, BOM, structure), ignoring declared content-types (l0113).
- Record full provenance (URL, timestamp, SHA-256 hash, byte count, declared vs sniffed type).
- Manifest and crawl completeness verification refusing to report complete on shortfall (l0122).
- Cross-source product agreement (e.g., CCT and wattage from Revit vs LDT) retaining both values
  and staying UNVERIFIED when divergent (l0118), and photometry vs fitting dimensions (l0098).
- Verification that "found" or "downloaded" claims have non-empty content on disk (l0072).
- Search result relevance filtering to prevent nonsense queries returning accidental hits (l0191).
- Isolation of test file outputs to prevent accidental writes into deployed asset stores (l0120).

Built on archpipe.evidence.

Reused components:
- archpipe.evidence: EvidenceRecord, EvidenceStatus, SourceRef, EvidenceError, VERIFIED, UNVERIFIED
- archpipe.luminaires.library: OLE_MAGIC identifier, zipfile/GLDF detection logic, eulumdat parsing
- archpipe.fixture_source: luminous opening vs fitting lens aspect/size comparison logic (l0098)
- archpipe.knowledge_index: stop-word list and minimum term match ratio for FTS/search relevance (l0191)

Quick Test:
    python -c "from archpipe.external_claims import sniff_content; print(sniff_content(b'PK\\x03\\x04')[0])"

Example Usage:
    >>> from archpipe.external_claims import sniff_content, ingest_bytes, check_manifest_completeness
    >>> sniffed_type, encoding = sniff_content(b'PK\\x03\\x04\\x14\\x00')
    >>> sniffed_type
    'zip'
    >>> record = ingest_bytes(b'PK\\x03\\x04', declared_type='application/json')
    >>> record.status.value
    'UNVERIFIED'
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
from typing import Any, Iterable
import zipfile

from archpipe.evidence import (
    EvidenceError,
    EvidenceRecord,
    EvidenceStatus,
    SourceRef,
    UNVERIFIED,
    VERIFIED,
)

ROOT = Path(__file__).resolve().parents[2]

OLE_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
UTF16_LE_BOM = b"\xff\xfe"
UTF16_BE_BOM = b"\xfe\xff"
UTF8_BOM = b"\xef\xbb\xbf"

DEFAULT_STOP_WORDS = frozenset({
    "the", "a", "an", "of", "for", "to", "in", "and", "or", "on", "at", "by", "with", "is", "be", "what"
})


class ExternalClaimError(EvidenceError, ValueError):
    """Base exception for external claim failures."""


class ContentTypeMismatchError(ExternalClaimError):
    """Raised when declared content-type contradicts sniffed byte content (l0113)."""


class CompletenessShortfallError(ExternalClaimError):
    """Raised when received item count falls short of expected manifest count (l0122)."""


class EmptyContentError(ExternalClaimError):
    """Raised when a found or downloaded claim points to empty content or folder (l0072)."""


class CrossSourceDisagreementError(ExternalClaimError):
    """Raised when independent sources disagree on product parameters (l0118, l0098)."""


class SearchRelevanceError(ExternalClaimError):
    """Raised when a search result fails the relevance / nonsense query threshold (l0191)."""


class UnsafeDestinationError(ExternalClaimError):
    """Raised when a test or unisolated process attempts to write into a deployed store (l0120)."""


@dataclass(frozen=True)
class ProvenanceRecord:
    """Provenance metadata for externally ingested data."""
    url: str | None = None
    retrieval_time: str = ""
    content_hash: str = ""
    byte_count: int = 0
    declared_type: str | None = None
    sniffed_type: str = "unknown"
    encoding: str | None = None
    type_matches: bool = True
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "content_hash": self.content_hash,
            "byte_count": self.byte_count,
            "sniffed_type": self.sniffed_type,
            "type_matches": self.type_matches,
        }
        if self.url is not None:
            data["url"] = self.url
        if self.retrieval_time:
            data["retrieval_time"] = self.retrieval_time
        if self.declared_type is not None:
            data["declared_type"] = self.declared_type
        if self.encoding is not None:
            data["encoding"] = self.encoding
        if self.notes:
            data["notes"] = self.notes
        return data


def normalize_type_label(declared: str | None) -> str | None:
    """Normalize MIME types, extensions, or labels to standard canonical tokens."""
    if not declared or not str(declared).strip():
        return None
    raw = str(declared).strip().lower().split(";")[0].strip()
    if raw.startswith("."):
        raw = raw[1:]
    mapping = {
        "application/json": "json",
        "json": "json",
        "application/zip": "zip",
        "application/x-zip-compressed": "zip",
        "zip": "zip",
        "application/pdf": "pdf",
        "pdf": "pdf",
        "text/plain": "txt",
        "txt": "txt",
        "revit_type_catalogue": "txt",
        "text/csv": "txt",
        "csv": "txt",
        "ies": "ies",
        "ldt": "ldt",
        "rfa": "rfa",
        "rvt": "rfa",
        "image/png": "image/png",
        "png": "image/png",
        "image/jpeg": "image/jpeg",
        "jpeg": "image/jpeg",
        "jpg": "image/jpeg",
        "model/gltf-binary": "gltf",
        "model/gltf+json": "gltf",
        "gltf": "gltf",
        "glb": "gltf",
        "text/html": "html",
        "html": "html",
    }
    return mapping.get(raw, raw)


def sniff_content(data: bytes) -> tuple[str, str | None]:
    """Identify content type and text encoding by byte inspections, never by declaration.
    
    Returns:
        (sniffed_type, encoding) where sniffed_type is one of:
        'zip', 'gldf', 'rfa', 'txt', 'ies', 'ldt', 'pdf', 'image/png',
        'image/jpeg', 'gltf', 'json', 'html', or 'unknown'.
    """
    if not data:
        return "empty", None

    # 1. Zip archive / GLDF container
    if data[:4] == b"PK\x03\x04":
        try:
            names = zipfile.ZipFile(io.BytesIO(data)).namelist()
            if any(n.lower().endswith("product.xml") for n in names):
                return "gldf", None
            return "zip", None
        except zipfile.BadZipFile:
            return "corrupt_zip", None

    # 2. OLE Compound Document (Revit .rfa / .rvt)
    if data[:8] == OLE_MAGIC:
        return "rfa", None

    # 3. PDF Document
    if data[:5] == b"%PDF-":
        return "pdf", None

    # 4. Standard Images
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png", None
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg", None

    # 5. Binary glTF
    if data[:4] == b"glTF":
        return "gltf", None

    # 6. UTF-16 BOM encodings (Revit type catalogues use UTF-16 with BOM)
    if data[:2] == UTF16_LE_BOM:
        try:
            text = data.decode("utf-16-le")
            if "##" in text[:400] or "," in text[:400]:
                return "txt", "utf-16-le"
            return "txt", "utf-16-le"
        except UnicodeDecodeError:
            return "unknown", "utf-16-le"
    if data[:2] == UTF16_BE_BOM:
        try:
            text = data.decode("utf-16-be")
            if "##" in text[:400] or "," in text[:400]:
                return "txt", "utf-16-be"
            return "txt", "utf-16-be"
        except UnicodeDecodeError:
            return "unknown", "utf-16-be"

    # 7. UTF-8 BOM
    if data[:3] == UTF8_BOM:
        try:
            text = data[3:].decode("utf-8")
            if text.lstrip().startswith("{") or text.lstrip().startswith("["):
                try:
                    json.loads(text)
                    return "json", "utf-8"
                except json.JSONDecodeError:
                    pass
            return "txt", "utf-8"
        except UnicodeDecodeError:
            return "unknown", "utf-8"

    # 8. Photometric IESNA
    head_latin1 = data[:400].decode("latin-1", "replace")
    if head_latin1.lstrip().upper().startswith("IESNA") or "TILT=" in head_latin1.upper()[:400]:
        return "ies", "latin-1"

    # 9. Eulumdat LDT Photometry
    # LDT files are lines of ASCII/Latin-1 text with strict header numbers
    from archpipe.luminaires import eulumdat as eu
    try:
        eu.parse(data.decode("latin-1"))
        return "ldt", "latin-1"
    except (eu.LDTError, Exception):
        pass

    # 10. JSON check (without BOM)
    stripped_head = head_latin1.lstrip()
    if stripped_head.startswith("{") or stripped_head.startswith("["):
        try:
            json.loads(data.decode("utf-8"))
            return "json", "utf-8"
        except (UnicodeDecodeError, json.JSONDecodeError):
            pass

    # 11. HTML check
    if stripped_head.lower().startswith("<!doctype html") or stripped_head.lower().startswith("<html"):
        return "html", "utf-8"

    # 12. Plain text / CSV with Revit headers
    if "##" in head_latin1[:400] and "," in head_latin1[:400]:
        return "txt", "latin-1"

    # Check if purely printable text
    try:
        data[:2000].decode("utf-8")
        return "txt", "utf-8"
    except UnicodeDecodeError:
        pass

    return "unknown", None


def ingest_bytes(
    data: bytes,
    declared_type: str | None = None,
    url: str | None = None,
    retrieval_time: str | None = None,
    scope: str = "item",
    allow_mismatch: bool = False,
) -> EvidenceRecord:
    """Ingest external payload by sniffing bytes, recording provenance, and verifying type consistency.
    
    Reproduces defect guard l0113 (Signify zip labelled application/json).
    
    Args:
        data: Raw payload bytes.
        declared_type: MIME type, file extension, or server header.
        url: Retrieval origin URL or path.
        retrieval_time: ISO 8601 string; defaults to current UTC time.
        scope: Scope of the resulting evidence record.
        allow_mismatch: If True, do not reduce status to UNVERIFIED on type mismatch.
        
    Returns:
        EvidenceRecord: VERIFIED if non-empty and type matches, otherwise UNVERIFIED.
    """
    ts = retrieval_time or datetime.now(timezone.utc).isoformat()
    content_hash = hashlib.sha256(data).hexdigest()
    byte_count = len(data)
    sniffed_type, encoding = sniff_content(data)

    norm_declared = normalize_type_label(declared_type)
    norm_sniffed = normalize_type_label(sniffed_type)

    # Empty payload check (l0072)
    if byte_count == 0:
        prov = ProvenanceRecord(
            url=url,
            retrieval_time=ts,
            content_hash=content_hash,
            byte_count=0,
            declared_type=declared_type,
            sniffed_type="empty",
            encoding=None,
            type_matches=False,
            notes="Payload is 0 bytes (l0072)",
        )
        src_ref = SourceRef(
            title=url or "External Ingest",
            url=url,
            verified=False,
            verification_method="byte sniffing",
            notes="Empty payload (0 bytes)",
        )
        return EvidenceRecord(
            value={"data": data, "provenance": prov.to_dict()},
            status=UNVERIFIED,
            source=src_ref,
            scope=scope,
            reasons=("External payload is empty (0 bytes) (l0072)",),
        )

    # Check for type mismatch (l0113)
    type_matches = True
    if norm_declared is not None and norm_declared not in ("application/octet-stream", "octet-stream", "unknown"):
        if norm_sniffed != norm_declared:
            # zip and gldf are compatible containers
            if not (norm_declared == "zip" and norm_sniffed == "gldf"):
                type_matches = False

    reasons: list[str] = []
    if not type_matches:
        reasons.append(
            f"Declared content type {declared_type!r} disagrees with sniffed content type {sniffed_type!r} (l0113)"
        )

    prov = ProvenanceRecord(
        url=url,
        retrieval_time=ts,
        content_hash=content_hash,
        byte_count=byte_count,
        declared_type=declared_type,
        sniffed_type=sniffed_type,
        encoding=encoding,
        type_matches=type_matches,
        notes="; ".join(reasons) if reasons else f"Sniffed as {sniffed_type}",
    )

    is_verified = type_matches or allow_mismatch
    src_ref = SourceRef(
        title=url or f"External {sniffed_type.upper()} Ingest",
        url=url,
        verified=is_verified,
        verification_method="byte sniffing and hash check",
        notes=f"sha256={content_hash[:16]}..., sniffed={sniffed_type}",
    )

    return EvidenceRecord(
        value={"data": data, "provenance": prov.to_dict()},
        status=VERIFIED if is_verified else UNVERIFIED,
        source=src_ref,
        scope=scope,
        reasons=tuple(reasons),
    )


def check_manifest_completeness(
    expected_count: int,
    received_count: int,
    label: str = "Manifest",
    min_coverage_ratio: float = 1.0,
    missing_items: list[str] | None = None,
    source_url: str | None = None,
) -> EvidenceRecord:
    """Compare expected vs received item counts and refuse to report complete on a shortfall.
    
    Reproduces defect guard l0122 (crawl that lost 41% of families but looked finished).
    
    Args:
        expected_count: Number of requested or listed items.
        received_count: Number of successfully crawled/ingested items.
        label: Descriptive label for the manifest or crawl.
        min_coverage_ratio: Minimum required ratio (defaults to 1.0 = 100% complete).
        missing_items: Optional list of missing identifiers.
        source_url: Source catalogue URL.
        
    Returns:
        EvidenceRecord: VERIFIED if received >= expected * min_coverage_ratio, UNVERIFIED on shortfall.
    """
    if expected_count < 0 or received_count < 0:
        raise ValueError("Counts must be non-negative integers")

    coverage = (received_count / expected_count) if expected_count > 0 else (1.0 if received_count == 0 else 0.0)
    shortfall = received_count < expected_count or coverage < min_coverage_ratio

    missing_count = max(0, expected_count - received_count)
    val = {
        "complete": not shortfall,
        "expected": expected_count,
        "received": received_count,
        "missing_count": missing_count,
        "coverage": round(coverage, 4),
        "min_coverage_ratio": min_coverage_ratio,
        "missing_items": missing_items or [],
    }

    reasons: list[str] = []
    if shortfall:
        reasons.append(
            f"{label} shortfall: received {received_count} of {expected_count} expected items "
            f"({coverage:.1%} < {min_coverage_ratio:.1%}, {missing_count} missing); "
            f"refuses to report complete (l0122)"
        )
    else:
        reasons.append(f"{label} complete: received {received_count} of {expected_count} items ({coverage:.1%})")

    src_ref = SourceRef(
        title=f"{label} Coverage Audit",
        url=source_url,
        verified=not shortfall,
        verification_method="manifest item count comparison",
        notes=reasons[0],
    )

    return EvidenceRecord(
        value=val,
        status=VERIFIED if not shortfall else UNVERIFIED,
        source=src_ref,
        reasons=tuple(reasons),
    )


def assert_manifest_complete(
    expected_count: int,
    received_count: int,
    label: str = "Manifest",
    min_coverage_ratio: float = 1.0,
    missing_items: list[str] | None = None,
) -> None:
    """Fail closed when a manifest or crawl has a shortfall."""
    rec = check_manifest_completeness(
        expected_count, received_count, label=label, min_coverage_ratio=min_coverage_ratio, missing_items=missing_items
    )
    if rec.status != VERIFIED:
        raise CompletenessShortfallError(rec.reasons[0])


def check_found_content(
    target: Path | str | bytes | list[Any] | dict[str, Any],
    name: str = "asset",
    source_url: str | None = None,
) -> EvidenceRecord:
    """Ensure that a claim of 'found' or 'downloaded' contains non-empty content on disk.
    
    Reproduces defect guard l0072 (props recorded as downloaded with empty folders).
    
    Args:
        target: File/directory path, bytes, string, list, or dict.
        name: Asset or package identifier.
        source_url: Download origin.
        
    Returns:
        EvidenceRecord: VERIFIED if non-empty, UNVERIFIED if empty or missing.
    """
    reasons: list[str] = []
    is_valid = True
    val: dict[str, Any] = {}

    if isinstance(target, Path):
        if not target.exists():
            is_valid = False
            reasons.append(f"Found claim for {name!r} rejected: path does not exist {target} (l0072)")
            val = {"path": str(target), "exists": False, "file_count": 0, "total_bytes": 0}
        elif target.is_dir():
            files = [p for p in target.rglob("*") if p.is_file()]
            non_empty_files = [p for p in files if p.stat().st_size > 0]
            total_bytes = sum(p.stat().st_size for p in non_empty_files)
            if not non_empty_files:
                is_valid = False
                reasons.append(
                    f"Found claim for {name!r} rejected: directory {target} contains no non-empty files (l0072)"
                )
            val = {
                "path": str(target),
                "exists": True,
                "is_dir": True,
                "file_count": len(non_empty_files),
                "total_bytes": total_bytes,
            }
        else:
            size = target.stat().st_size
            if size == 0:
                is_valid = False
                reasons.append(f"Found claim for {name!r} rejected: file {target} is 0 bytes (l0072)")
            val = {"path": str(target), "exists": True, "is_file": True, "total_bytes": size}
    elif isinstance(target, (bytes, str)):
        length = len(target.strip()) if isinstance(target, str) else len(target)
        if length == 0:
            is_valid = False
            reasons.append(f"Found claim for {name!r} rejected: payload is 0 bytes/characters (l0072)")
        val = {"length": length}
    elif isinstance(target, (list, dict)):
        if len(target) == 0:
            is_valid = False
            reasons.append(f"Found claim for {name!r} rejected: collection has 0 elements (l0072)")
        val = {"item_count": len(target)}
    else:
        if target is None:
            is_valid = False
            reasons.append(f"Found claim for {name!r} rejected: target is None (l0072)")
        val = {"target": str(target)}

    src_ref = SourceRef(
        title=f"Non-empty Content Audit: {name}",
        url=source_url,
        verified=is_valid,
        verification_method="disk and byte verification",
        notes="; ".join(reasons) if reasons else "Non-empty content confirmed",
    )

    return EvidenceRecord(
        value=val,
        status=VERIFIED if is_valid else UNVERIFIED,
        source=src_ref,
        reasons=tuple(reasons),
    )


def assert_found_content(
    target: Path | str | bytes | list[Any] | dict[str, Any],
    name: str = "asset",
) -> None:
    """Fail closed when content for a found claim is empty."""
    rec = check_found_content(target, name=name)
    if rec.status != VERIFIED:
        raise EmptyContentError(rec.reasons[0])


def check_cct_and_watts_agreement(
    source_a: dict[str, Any],
    source_b: dict[str, Any],
    cct_tolerance_k: float = 50.0,
    watts_tolerance_w: float = 0.5,
    source_a_label: str = "Source A",
    source_b_label: str = "Source B",
) -> EvidenceRecord:
    """Check cross-source agreement on CCT and power; stays UNVERIFIED with both values on drift.
    
    Reproduces defect guard l0118 (Signify Revit family claiming 3200 K / 3 W vs LDT 3000 K / 23 W).
    
    Args:
        source_a: First source dict containing 'cct' (or 'cct_k') and 'watts' (or 'w').
        source_b: Second source dict containing 'cct' (or 'cct_k') and 'watts' (or 'w').
        cct_tolerance_k: Maximum allowable colour temperature difference in Kelvin.
        watts_tolerance_w: Maximum allowable power difference in Watts.
        source_a_label: Label for the first source (e.g. 'revit_family').
        source_b_label: Label for the second source (e.g. 'ldt_file').
        
    Returns:
        EvidenceRecord: VERIFIED if both agree, otherwise UNVERIFIED retaining both values.
    """
    def _get_val(d: dict[str, Any], *keys: str) -> float | None:
        for k in keys:
            if k in d and d[k] is not None:
                try:
                    return float(d[k])
                except (ValueError, TypeError):
                    pass
        return None

    cct_a = _get_val(source_a, "cct_k", "cct", "colour_temperature")
    cct_b = _get_val(source_b, "cct_k", "cct", "colour_temperature")
    watts_a = _get_val(source_a, "watts", "w", "power")
    watts_b = _get_val(source_b, "watts", "w", "power")

    discrepancies: list[str] = []
    drift_cct = abs(cct_a - cct_b) if (cct_a is not None and cct_b is not None) else None
    drift_watts = abs(watts_a - watts_b) if (watts_a is not None and watts_b is not None) else None

    if drift_cct is not None and drift_cct > cct_tolerance_k:
        discrepancies.append(
            f"CCT mismatch: {source_a_label} ({cct_a:.0f} K) vs {source_b_label} ({cct_b:.0f} K) "
            f"exceeds tolerance {cct_tolerance_k:.0f} K (drift {drift_cct:.0f} K) (l0118)"
        )
    if drift_watts is not None and drift_watts > watts_tolerance_w:
        discrepancies.append(
            f"Watts mismatch: {source_a_label} ({watts_a:.1f} W) vs {source_b_label} ({watts_b:.1f} W) "
            f"exceeds tolerance {watts_tolerance_w:.1f} W (drift {drift_watts:.1f} W) (l0118)"
        )

    has_conflict = bool(discrepancies)

    val = {
        "agreed": not has_conflict,
        "cct": {source_a_label: cct_a, source_b_label: cct_b, "drift": drift_cct, "tolerance": cct_tolerance_k},
        "watts": {source_a_label: watts_a, source_b_label: watts_b, "drift": drift_watts, "tolerance": watts_tolerance_w},
        "source_a": source_a,
        "source_b": source_b,
        "discrepancies": discrepancies,
    }

    src_ref = SourceRef(
        title=f"Cross-Source Agreement ({source_a_label} vs {source_b_label})",
        verified=not has_conflict,
        verification_method="cross-source tolerance comparison",
        notes="; ".join(discrepancies) if discrepancies else "Parameters agreed within tolerance",
    )

    return EvidenceRecord(
        value=val,
        status=VERIFIED if not has_conflict else UNVERIFIED,
        source=src_ref,
        reasons=tuple(discrepancies) if discrepancies else ("CCT and watts agree within tolerance",),
    )


def check_photometry_fitting_agreement(
    ies_dims_mm: tuple[float, ...] | list[float],
    fitting_lens_dims_mm: tuple[float, float] | list[float],
    size_ratio_max: float = 2.0,
    aspect_ratio_max: float = 3.0,
    fitting_label: str = "fitting",
) -> EvidenceRecord:
    """Verify that an IES luminous opening matches the physical fitting lens dimensions and aspect.
    
    Reproduces defect guard l0098 (a strip-light photometry file attached to a round drum).
    Reuses the ratio bounds from archpipe.fixture_source.photometry_matches_fitting.
    
    Args:
        ies_dims_mm: Plan dimensions of the IES luminous opening in mm (length, width).
        fitting_lens_dims_mm: Plan dimensions of the physical fitting lens in mm (length, width).
        size_ratio_max: Maximum allowable ratio between longest extents (defaults to 2.0).
        aspect_ratio_max: Maximum allowable ratio between aspect ratios (defaults to 3.0).
        fitting_label: Identifier of the light fitting.
        
    Returns:
        EvidenceRecord: VERIFIED if plausible, UNVERIFIED if photometric file describes a different product.
    """
    valid_ies = sorted((abs(float(v)) for v in ies_dims_mm[:2] if abs(float(v)) > 0.5), reverse=True)
    valid_lens = sorted((abs(float(v)) for v in fitting_lens_dims_mm[:2] if abs(float(v)) > 0.5), reverse=True)

    if not valid_ies or not valid_lens:
        return EvidenceRecord(
            value={"agreed": False, "reason": "Missing or zero dimensions"},
            status=UNVERIFIED,
            source=SourceRef(title=f"Photometry Agreement: {fitting_label}", verified=False),
            reasons=("Photometry or lens dimensions are missing or zero",),
        )

    ies_long = valid_ies[0]
    ies_short = valid_ies[1] if len(valid_ies) > 1 else valid_ies[0]
    lens_long = valid_lens[0]
    lens_short = valid_lens[1] if len(valid_lens) > 1 else valid_lens[0]

    size_ratio = ies_long / max(lens_long, 1e-6)
    size_ok = (1.0 / size_ratio_max) <= size_ratio <= size_ratio_max

    ies_aspect = ies_long / max(ies_short, 1.0)
    lens_aspect = lens_long / max(lens_short, 1.0)
    aspect_ratio = max(ies_aspect, lens_aspect) / max(min(ies_aspect, lens_aspect), 1e-6)
    aspect_ok = aspect_ratio <= aspect_ratio_max

    problems: list[str] = []
    if not size_ok:
        problems.append(
            f"Photometric file describes a different product: IES opening {ies_long:.0f} mm vs fitting lens {lens_long:.0f} mm "
            f"(size ratio {size_ratio:.2f} outside 1/{size_ratio_max:.0f}..{size_ratio_max:.0f}) (l0098)"
        )
    if not aspect_ok:
        problems.append(
            f"Photometric file describes a different product: IES shape {ies_aspect:.1f}:1 vs fitting lens {lens_aspect:.1f}:1 "
            f"(aspect ratio drift {aspect_ratio:.1f} > {aspect_ratio_max:.1f}) (l0098)"
        )

    has_mismatch = bool(problems)

    val = {
        "agreed": not has_mismatch,
        "ies_dims_mm": [ies_long, ies_short],
        "fitting_lens_dims_mm": [lens_long, lens_short],
        "size_ratio": round(size_ratio, 3),
        "aspect_ratio": round(aspect_ratio, 3),
        "problems": problems,
    }

    src_ref = SourceRef(
        title=f"Photometry Agreement: {fitting_label}",
        verified=not has_mismatch,
        verification_method="photometric dimensions vs physical lens comparison",
        notes="; ".join(problems) if problems else "Photometry dimensions match fitting lens",
    )

    return EvidenceRecord(
        value=val,
        status=VERIFIED if not has_mismatch else UNVERIFIED,
        source=src_ref,
        reasons=tuple(problems) if problems else ("Photometry matches fitting shape and size within tolerance",),
    )


def check_search_relevance(
    query: str,
    text: str,
    stop_words: frozenset[str] = DEFAULT_STOP_WORDS,
    min_match_ratio: float = 0.5,
    min_words: int = 2,
    source_title: str = "Search Query Relevance",
) -> EvidenceRecord:
    """Verify that a search result satisfies the query relevance threshold (nonsense query control).
    
    Reproduces defect guard l0191 (nonsense query fallback returning spurious page hit).
    Reuses stop-word elimination and minimum-word matching logic from archpipe.knowledge_index.
    
    Args:
        query: User or pipeline query string.
        text: Matched page or document content.
        stop_words: Set of words ignored during scoring.
        min_match_ratio: Minimum fraction of non-stop words required (defaults to 0.5).
        min_words: Minimum absolute number of distinct non-stop words required (defaults to 2).
        source_title: Source record title.
        
    Returns:
        EvidenceRecord: VERIFIED if relevance threshold is cleared, UNVERIFIED if rejected.
    """
    words = [w.lower() for w in re.findall(r"[\w.]+", query) if w.lower() not in stop_words]
    unique_words = set(words)

    if not unique_words:
        return EvidenceRecord(
            value={"hit": False, "query": query, "matched_words": [], "query_words": []},
            status=UNVERIFIED,
            source=SourceRef(title=source_title, verified=False),
            reasons=(f"Query {query!r} has no searchable words after stop-word removal",),
        )

    # For a 1-word query, 1 word is needed. For multi-word queries, require at least
    # max(min_words, ceil(len * min_match_ratio)) or (len + 1) // 2.
    if len(unique_words) == 1:
        need = 1
    else:
        need = max(min_words, (len(unique_words) + 1) // 2)

    lower_text = text.lower()
    matched = [w for w in unique_words if w in lower_text]
    hit_cleared = len(matched) >= need

    reasons: list[str] = []
    if not hit_cleared:
        reasons.append(
            f"Search result rejected by relevance check: matched {len(matched)} of {len(unique_words)} "
            f"distinct query words (needed at least {need}) for query {query!r} (l0191)"
        )
    else:
        reasons.append(
            f"Search result cleared relevance check: matched {len(matched)} of {len(unique_words)} words (needed {need})"
        )

    val = {
        "hit": hit_cleared,
        "query": query,
        "query_words": sorted(unique_words),
        "matched_words": sorted(matched),
        "matched_count": len(matched),
        "needed_count": need,
        "match_ratio": round(len(matched) / len(unique_words), 3),
    }

    src_ref = SourceRef(
        title=source_title,
        verified=hit_cleared,
        verification_method="search query term coverage check",
        notes=reasons[0],
    )

    return EvidenceRecord(
        value=val,
        status=VERIFIED if hit_cleared else UNVERIFIED,
        source=src_ref,
        reasons=tuple(reasons),
    )


def filter_search_results(
    query: str,
    results: list[dict[str, Any]],
    text_key: str = "text",
    stop_words: frozenset[str] = DEFAULT_STOP_WORDS,
) -> list[dict[str, Any]]:
    """Filter candidate search hits, discarding any that fail the relevance check."""
    out: list[dict[str, Any]] = []
    for r in results:
        content = str(r.get(text_key, "") or "")
        chk = check_search_relevance(query, content, stop_words=stop_words)
        if chk.status == VERIFIED and chk.value.get("hit"):
            out.append(r)
    return out


def _path_contains(parent: Path, child: Path) -> bool:
    """Check if child path is inside or identical to parent directory, handling Windows differences."""
    pairs: list[tuple[Path, Path]] = [(child, parent)]
    try:
        pairs.append((child.resolve(), parent.resolve()))
    except Exception:
        pass
    try:
        pairs.append((child.absolute(), parent.absolute()))
    except Exception:
        pass

    for c, p in pairs:
        try:
            c.relative_to(p)
            return True
        except ValueError:
            pass

    def _to_norm_parts(path_obj: Path | str) -> list[str]:
        raw = str(path_obj)
        if raw.startswith("\\\\?\\") or raw.startswith("//?/"):
            raw = raw[4:]
        norm = os.path.normpath(raw)
        if os.name == "nt":
            norm = os.path.normcase(norm)
        return [part for part in re.split(r"[\\/]+", norm) if part]

    for c, p in pairs:
        c_parts = _to_norm_parts(c)
        p_parts = _to_norm_parts(p)
        if len(c_parts) >= len(p_parts) and c_parts[:len(p_parts)] == p_parts:
            return True

    return False


def check_safe_destination(
    dest: Path,
    forbidden_roots: list[Path] | None = None,
    allowed_roots: list[Path] | None = None,
) -> Path:
    """Ensure a file write destination is safe and isolated from production asset repositories.
    
    Reproduces defect guard l0120 (unit test exported synthetic IES into deployed product folder).
    
    Args:
        dest: Target output path.
        forbidden_roots: Directories that must NEVER be written to by tests or unisolated workers.
        allowed_roots: If provided, dest MUST resolve within one of these directories.
        
    Returns:
        The validated Path object.
        
    Raises:
        UnsafeDestinationError: If dest falls into a forbidden root or outside allowed roots.
    """
    dest = Path(dest)

    default_forbidden = [
        ROOT / "assets/user",
        ROOT / "assets/props",
        ROOT / "knowledge/sources",
    ]
    roots_forbidden = forbidden_roots or default_forbidden

    for fb in roots_forbidden:
        if _path_contains(Path(fb), dest):
            raise UnsafeDestinationError(
                f"Destination {dest} is inside deployed repository {fb}; writes must be isolated (l0120)"
            )

    if allowed_roots:
        allowed = any(_path_contains(Path(ar), dest) for ar in allowed_roots)
        if not allowed:
            raise UnsafeDestinationError(
                f"Destination {dest} is outside allowed directories {allowed_roots} (l0120)"
            )

    return dest
