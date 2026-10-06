"""Tests for archpipe.evidence: evidence status, promotion guards, and defect cases.

Reproduces real failure cases from docs/LEARNINGS.md frozen by value:
- l0188: Book file named '6th ed. 2023' whose copyright is 2nd ed. 1980 stays UNVERIFIED until verify().
- l0189: PDF page label vs printed page mismatch (191 vs 5.45) recorded and caught.
- l0092: ASSUMED item combined with VERIFIED items yields ASSUMED.
- l0020: Room-scoped result applied to dwelling raises ScopeWideningError unless rescoped with reason.
- l0179: Model metadata (408 mm) disagreeing with measured geometry (202 mm) is flagged.
- l0763: Render-side fix cannot promote design status.
- l0661: Render and daylight analysis require matching model hash.
Plus corresponding quiet cases.

Quick Test:
    python -m unittest tests/test_evidence.py
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from archpipe.evidence import (
    EvidenceRecord,
    EvidenceStatus,
    SourceRef,
    ClientDecision,
    combine,
    verify,
    rescope,
    check_book_edition,
    check_page_locator,
    assert_page_agreement,
    check_geometry_against_metadata,
    assert_geometry_matches_metadata,
    check_render_vs_design,
    check_shared_model,
    from_guidance_card,
    ScopeWideningError,
    PageMismatchError,
    GeometryDisagreementError,
    VERIFIED,
    ASSUMED,
    UNVERIFIED,
    REQUIREMENT,
    CLIENT_DECISION,
)


class EvidenceStatusTests(unittest.TestCase):
    """Test promotion rules, status hierarchy and verify() discipline."""

    def test_cannot_construct_verified_record_without_verified_source(self) -> None:
        # A record cannot claim VERIFIED status without an explicitly verified source
        with self.assertRaises(ValueError):
            EvidenceRecord(value=900, status=VERIFIED, source=None)

        unverified_source = SourceRef(title="Unchecked Book", verified=False)
        with self.assertRaises(ValueError):
            EvidenceRecord(value=900, status=VERIFIED, source=unverified_source)

    def test_verify_promotes_record_recording_checked_source(self) -> None:
        rec = EvidenceRecord(
            value=900,
            status=UNVERIFIED,
            source=SourceRef(title="Neufert Architects Data", edition="2nd English ed. 1980", verified=False),
        )
        self.assertEqual(rec.status, UNVERIFIED)

        verified_rec = rec.verify(
            source=SourceRef(
                title="Neufert Architects Data",
                edition="2nd English ed. 1980",
                printed_page="17",
                verified=True,
                notes="Checked copyright page and Table 1 row B",
            ),
            checked_by="lead",
        )
        self.assertEqual(verified_rec.status, VERIFIED)
        self.assertTrue(verified_rec.source.verified)
        self.assertEqual(verified_rec.source.printed_page, "17")
        self.assertEqual(len(verified_rec.verification_history), 1)
        self.assertEqual(verified_rec.verification_history[0]["checked_by"], "lead")

    def test_client_decision_requires_who_when_and_reason(self) -> None:
        # CLIENT_DECISION requires decided_by, valid ISO date, and reason
        with self.assertRaises(ValueError):
            EvidenceRecord(value="16mm", status=CLIENT_DECISION, client_decision=None)

        with self.assertRaises(ValueError):
            ClientDecision(decided_by="", date="2026-09-28", reason="Requested wide angle")

        with self.assertRaises(ValueError):
            ClientDecision(decided_by="client", date="not-an-iso-date", reason="Requested wide angle")

        decision = ClientDecision(decided_by="client", date="2026-09-28", reason="Client requested 16mm lens")
        rec = EvidenceRecord(value="16mm", status=CLIENT_DECISION, client_decision=decision)
        self.assertEqual(rec.status, CLIENT_DECISION)
        self.assertEqual(rec.client_decision.decided_by, "client")
        self.assertEqual(rec.client_decision.date, "2026-09-28")

    def test_weakest_status_hierarchy_combinations(self) -> None:
        # Combining values yields the WEAKEST status across all five statuses
        v = EvidenceRecord(
            value=1,
            status=VERIFIED,
            source=SourceRef(title="Source 1", verified=True),
        )
        req = EvidenceRecord(value=2, status=REQUIREMENT)
        cd = EvidenceRecord(
            value=3,
            status=CLIENT_DECISION,
            client_decision=ClientDecision(decided_by="client", date="2026-09-28", reason="Client choice"),
        )
        assumed = EvidenceRecord(value=4, status=ASSUMED)
        unverified = EvidenceRecord(value=5, status=UNVERIFIED)

        # VERIFIED + REQUIREMENT -> REQUIREMENT
        self.assertEqual(combine(v, req).status, REQUIREMENT)

        # REQUIREMENT + CLIENT_DECISION -> CLIENT_DECISION
        self.assertEqual(combine(req, cd).status, CLIENT_DECISION)

        # CLIENT_DECISION + ASSUMED -> ASSUMED
        self.assertEqual(combine(cd, assumed).status, ASSUMED)

        # ASSUMED + UNVERIFIED -> UNVERIFIED
        self.assertEqual(combine(assumed, unverified).status, UNVERIFIED)

        # VERIFIED + UNVERIFIED -> UNVERIFIED
        self.assertEqual(combine(v, unverified).status, UNVERIFIED)

        # All five combined -> UNVERIFIED (the weakest of all)
        self.assertEqual(combine(v, req, cd, assumed, unverified).status, UNVERIFIED)


class RealDefectReproductionTests(unittest.TestCase):
    """Reproduce the 12 specific defect lessons frozen as real case data."""

    def test_l0188_book_filename_edition_mismatch_stays_unverified_until_verify(self) -> None:
        """Lesson l0188: Book file named 'Neufert 6th ed. 2023' is actually 1980 2nd edition.
        
        The file name was trusted as current until the copyright page revealed
        the true 1980 2nd edition. The evidence record must stay UNVERIFIED
        until verify() records the true copyright page.
        """
        filename = "Neufert Architects Data 6th ed. 2023.pdf"
        copyright_edition = "2nd English edition 1980"

        # Audit helper detects the discrepancy
        check = check_book_edition(filename, copyright_edition)
        self.assertTrue(check["flagged"])
        self.assertFalse(check["matches"])
        self.assertEqual(check["status"], UNVERIFIED)
        self.assertIn("6th", check["mismatches"][0])

        # Record constructed from the downloaded file starts UNVERIFIED
        rec = EvidenceRecord(
            value={"corridor_min_width_mm": 900},
            status=UNVERIFIED,
            source=SourceRef(
                title="Neufert Architects' Data",
                file_edition="6th ed. 2023",
                edition="6th ed. 2023",
                verified=False,
                notes="Candidate downloaded file",
            ),
        )
        self.assertEqual(rec.status, UNVERIFIED)

        # Explicit verify() records the checked copyright page and edition
        verified_rec = rec.verify(
            source=SourceRef(
                title="Neufert Architects' Data",
                edition="2nd English ed. 1980",
                file_edition="6th ed. 2023",
                printed_page="17",
                verified=True,
                notes="Copyright page checked: 1980 2nd English edition; filename 6th ed. was incorrect (l0188)",
            ),
            checked_by="lead",
        )
        self.assertEqual(verified_rec.status, VERIFIED)
        self.assertEqual(verified_rec.source.edition, "2nd English ed. 1980")
        self.assertEqual(verified_rec.source.file_edition, "6th ed. 2023")

    def test_l0188_edition_match_quiet_case(self) -> None:
        """Quiet case for l0188: when filename claim agrees with copyright page."""
        filename = "Metric_Handbook_7th_ed_2022.pdf"
        copyright_edition = "7th edition 2022"
        check = check_book_edition(filename, copyright_edition)
        self.assertFalse(check["flagged"])
        self.assertTrue(check["matches"])
        self.assertEqual(check["status"], VERIFIED)

    def test_l0189_pdf_page_label_vs_printed_page_mismatch_caught(self) -> None:
        """Lesson l0189: Building Construction Illustrated PDF page labels are sequence numbers.
        
        The PDF label displays '191' while the printed edge number is '5.45'.
        Trusting PDF labels as printed pages causes false citations.
        """
        pdf_label = 191
        printed_page = "5.45"

        check = check_page_locator(pdf_label=pdf_label, printed_page=printed_page)
        self.assertTrue(check["flagged"])
        self.assertFalse(check["matches"])
        self.assertFalse(check["reliable"])

        # Fail-closed guard raises on disagreement
        with self.assertRaises(PageMismatchError) as ctx:
            assert_page_agreement(pdf_label, printed_page)
        self.assertIn("disagrees with printed page", str(ctx.exception))
        self.assertIn("l0189", str(ctx.exception))

        # SourceRef reflects page mismatch property
        src = SourceRef(
            title="Building Construction Illustrated",
            edition="4th ed.",
            pdf_label="191",
            printed_page="5.45",
        )
        self.assertTrue(src.has_page_mismatch)

    def test_l0189_page_locator_agreement_quiet_case(self) -> None:
        """Quiet case for l0189: when PDF page label matches printed page."""
        check = check_page_locator(pdf_label="17", printed_page="17")
        self.assertFalse(check["flagged"])
        self.assertTrue(check["matches"])
        self.assertTrue(check["reliable"])
        # Does not raise
        assert_page_agreement("17", "17")

    def test_l0092_assumed_item_combined_with_verified_yields_assumed(self) -> None:
        """Lesson l0092: Invented dressing and stand-ins indistinguishable from design content.
        
        When verified design furniture is combined with an assumed dressing item
        or stand-in (e.g. decor, unverified prop), the composite result must be
        ASSUMED, not promoted to VERIFIED.
        """
        bed = EvidenceRecord(
            value={"name": "bed_king", "width_mm": 1930, "depth_mm": 2030},
            status=VERIFIED,
            source=SourceRef(title="Revit Model Extract", edition="2027", verified=True),
            scope="room:bedroom",
        )
        nightstand = EvidenceRecord(
            value={"name": "bedside_table", "width_mm": 500, "depth_mm": 450},
            status=VERIFIED,
            source=SourceRef(title="Revit Model Extract", edition="2027", verified=True),
            scope="room:bedroom",
        )
        dressing_vase = EvidenceRecord(
            value={"name": "decor_vase", "bounds_m": [0.2, 0.3, 0.2]},
            status=ASSUMED,
            source=SourceRef(title="Procedural Stand-in", verified=False),
            scope="room:bedroom",
            reasons=("Invented dressing stand-in, not design content (l0092)",),
        )

        composite = combine(bed, nightstand, dressing_vase, value="bedroom_furnishing_cluster")
        self.assertEqual(composite.status, ASSUMED)
        self.assertIn("Combined status reduced to ASSUMED", composite.reasons[0])

    def test_l0092_all_verified_combination_quiet_case(self) -> None:
        """Quiet case for l0092: when all components are VERIFIED, composite is VERIFIED."""
        bed = EvidenceRecord(
            value="bed",
            status=VERIFIED,
            source=SourceRef(title="Revit Extract", verified=True),
            scope="room",
        )
        nightstand = EvidenceRecord(
            value="table",
            status=VERIFIED,
            source=SourceRef(title="Revit Extract", verified=True),
            scope="room",
        )
        composite = combine(bed, nightstand)
        self.assertEqual(composite.status, VERIFIED)

    def test_l0020_room_scoped_result_applied_to_dwelling_raises(self) -> None:
        """Lesson l0020: An isolated room is not a dwelling.
        
        A pass in one room (e.g. bedroom area or lighting) cannot be silently
        promoted to dwelling scope. Applying room scope to dwelling scope
        without an explicit re-scoping and reason raises ScopeWideningError.
        """
        bedroom_lux = EvidenceRecord(
            value={"maintained_lux": 320},
            status=VERIFIED,
            source=SourceRef(title="Bedroom Lighting Calc", verified=True),
            scope="room",
        )

        # Applying directly to dwelling scope raises
        with self.assertRaises(ScopeWideningError) as ctx:
            bedroom_lux.apply_to("dwelling")
        self.assertIn("Scope cannot widen silently from 'room' to 'dwelling'", str(ctx.exception))
        self.assertIn("lesson l0020", str(ctx.exception))

        # Combining room-scoped and dwelling-scoped records yields room scope (narrowest)
        dwelling_req = EvidenceRecord(
            value={"dwelling_target_lux": 300},
            status=REQUIREMENT,
            scope="dwelling",
        )
        combined = combine(bedroom_lux, dwelling_req)
        self.assertEqual(combined.scope, "room")

        # Attempting to force dwelling scope on combination without reason raises
        with self.assertRaises(ScopeWideningError):
            combine(bedroom_lux, dwelling_req, scope="dwelling")

    def test_l0020_rescoping_with_reason_allows_dwelling_application(self) -> None:
        """Explicit re-scoping with an authored reason permits scope widening."""
        bedroom_lux = EvidenceRecord(
            value={"maintained_lux": 320},
            status=VERIFIED,
            source=SourceRef(title="Bedroom Lighting Calc", verified=True),
            scope="room",
        )

        # Re-scoping requires a non-empty reason
        with self.assertRaises(ValueError):
            bedroom_lux.rescope(target_scope="dwelling", reason="")

        rescoped = bedroom_lux.rescope(
            target_scope="dwelling",
            reason="Client approved bedroom lighting method as whole-dwelling benchmark",
            decided_by="lead",
        )
        self.assertEqual(rescoped.scope, "dwelling")
        # Now apply_to dwelling succeeds quietly
        applied = rescoped.apply_to("dwelling")
        self.assertEqual(applied.scope, "dwelling")
        self.assertEqual(len(applied.rescope_history), 1)
        self.assertEqual(applied.rescope_history[0]["from_scope"], "room")
        self.assertEqual(applied.rescope_history[0]["to_scope"], "dwelling")

    def test_l0020_same_scope_and_narrowing_quiet_cases(self) -> None:
        """Quiet cases for scope application: same scope and narrowing are allowed."""
        room_rec = EvidenceRecord(value=10, status=VERIFIED, source=SourceRef("s", verified=True), scope="room")
        # Same scope succeeds
        self.assertEqual(room_rec.apply_to("room").scope, "room")

        # Narrowing: dwelling rule applied to room succeeds
        dwelling_rec = EvidenceRecord(value=2400, status=REQUIREMENT, scope="dwelling")
        self.assertEqual(dwelling_rec.apply_to("room").scope, "dwelling")

    def test_l0179_model_metadata_disagrees_with_measured_geometry_flagged(self) -> None:
        """Lesson l0179: A model genuinely disagrees with its metadata.
        
        desk_lamp_arm_01 declared depth 408 mm in metadata but measured 202 mm
        in glTF mesh. The defect is flagged as failed and never silently repaired.
        """
        metadata_depth_mm = 408.0
        measured_mesh_depth_mm = 202.0

        check = check_geometry_against_metadata(
            metadata_dimension=metadata_depth_mm,
            measured_dimension=measured_mesh_depth_mm,
            tolerance=5.0,
            unit="mm",
        )
        self.assertTrue(check["flagged"])
        self.assertFalse(check["matches"])
        self.assertEqual(check["status"], UNVERIFIED)
        self.assertAlmostEqual(check["drift"], 206.0, places=1)
        self.assertIn("l0179", check["reason"])

        # Fail closed check raises
        with self.assertRaises(GeometryDisagreementError) as ctx:
            assert_geometry_matches_metadata(metadata_depth_mm, measured_mesh_depth_mm, tolerance=5.0)
        self.assertIn("disagrees with measured geometry", str(ctx.exception))

    def test_l0179_model_metadata_matches_measured_geometry_quiet_case(self) -> None:
        """Quiet case for l0179: metadata dimension matches measured geometry within tolerance."""
        check = check_geometry_against_metadata(408.0, 408.2, tolerance=1.0, unit="mm")
        self.assertFalse(check["flagged"])
        self.assertTrue(check["matches"])
        self.assertEqual(check["status"], VERIFIED)
        # Does not raise
        assert_geometry_matches_metadata(408.0, 408.2, tolerance=1.0)

    def test_l0763_render_side_fix_cannot_promote_design_status(self) -> None:
        """Lesson l0763: A render-side fix is not a design fix.
        
        Moving 14 light fittings in the render only was presented as a fix,
        while the Revit design spec still put them 100-155 mm off the ceiling.
        Render-side adjustments diverging from design are flagged.
        """
        design_fitting_z = 2545.0  # mm
        render_fitting_z = 2700.0  # mm (render seating moved it)
        check = check_render_vs_design(design_fitting_z, render_fitting_z, tolerance=1.0)
        self.assertTrue(check["flagged"])
        self.assertFalse(check["matches"])
        self.assertEqual(check["status"], UNVERIFIED)
        self.assertIn("l0763", check["reason"])

        # Quiet case: render matches design
        quiet_check = check_render_vs_design(2700.0, 2700.0, tolerance=1.0)
        self.assertFalse(quiet_check["flagged"])
        self.assertTrue(quiet_check["matches"])

    def test_l0661_render_and_daylight_analysis_require_matching_model_hash(self) -> None:
        """Lesson l0661: Render and daylight analysis now describe one building.
        
        Using different geometry or reflectances across render and daylight
        studies fails the shared building consistency check.
        """
        render_hash = "a" * 64
        daylight_hash = "b" * 64
        check = check_shared_model(render_hash, daylight_hash)
        self.assertTrue(check["flagged"])
        self.assertFalse(check["matches"])
        self.assertEqual(check["status"], UNVERIFIED)
        self.assertIn("l0661", check["reason"])

        # Quiet case: both describe the same model hash
        quiet = check_shared_model(render_hash, render_hash)
        self.assertFalse(quiet["flagged"])
        self.assertTrue(quiet["matches"])
        self.assertEqual(quiet["status"], VERIFIED)

    def test_guidance_card_integration_reuses_guidance_and_sources(self) -> None:
        """Test reuse of guidance.py and sources.py data structures."""
        # Verified card
        verified_card = {
            "id": "ndss-double-bedroom-area",
            "source_id": "uk-ndss",
            "edition": "2015",
            "locator": "Table 1 row A",
            "status": "verified",
            "category": "technical_requirement",
            "unit": "m2",
            "verified_value": 11.5,
            "conditions": "Dwelling bedroom area",
            "verification": "Original standard Table 1 checked",
        }
        sources = {
            "uk-ndss": {
                "id": "uk-ndss",
                "title": "Nationally Described Space Standard",
                "edition": "2015",
                "status": "content_verified",
            }
        }
        rec = from_guidance_card(verified_card, sources)
        self.assertEqual(rec.status, VERIFIED)
        self.assertEqual(rec.value, 11.5)
        self.assertEqual(rec.source.title, "Nationally Described Space Standard")

        # Unverified card with wrong edition
        unverified_card = dict(verified_card, edition="1999", status="unverified")
        unverified_rec = from_guidance_card(unverified_card, sources)
        self.assertEqual(unverified_rec.status, UNVERIFIED)

    def test_serialization_round_trip(self) -> None:
        """Test to_dict and from_dict preserve all metadata, history and statuses."""
        decision = ClientDecision(decided_by="client", date="2026-09-28", reason="Requested 16mm lens")
        src = SourceRef(title="AD M", edition="2015", printed_page="17", verified=False)
        rec = EvidenceRecord(
            value={"width": 900},
            status=CLIENT_DECISION,
            source=src,
            scope="room:bedroom",
            client_decision=decision,
        )
        rescoped = rec.rescope("dwelling", reason="Approved as whole-dwelling standard", decided_by="lead")

        data = rescoped.to_dict()
        reconstructed = EvidenceRecord.from_dict(data)

        self.assertEqual(reconstructed.status, CLIENT_DECISION)
        self.assertEqual(reconstructed.scope, "dwelling")
        self.assertEqual(reconstructed.client_decision.decided_by, "client")
        self.assertEqual(reconstructed.client_decision.date, "2026-09-28")
        self.assertEqual(reconstructed.value, {"width": 900})
        self.assertEqual(len(reconstructed.rescope_history), 1)
        self.assertEqual(reconstructed.rescope_history[0]["reason"], "Approved as whole-dwelling standard")


if __name__ == "__main__":
    unittest.main()
