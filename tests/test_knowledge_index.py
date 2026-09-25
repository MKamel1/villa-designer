"""Knowledge index: known answers come back in the top 5 with the printed page a
citation needs; nonsense returns nothing; the dictionary resolves index terms.
The expected pages were read by hand from the held originals (2026-09-24).
Skipped where the private index is not built on this machine."""
import unittest

from archpipe import knowledge_index as k

ADM = "uk-ad-m#BR_PDF_AD_M1_2015_with_2016_amendments_V3"

# (query, book, printed page or EPUB section fragment)
GOLDEN = [
    ("minimum clear width of every hall or landing", ADM, "17"),
    ("headroom for stairs", "uk-ad-k", "7"),
    ("maximum pitch for a private stair", "uk-ad-k", "5"),
    ("worktop heights between 700mm and 950mm", ADM, "38"),
    ("width per person should be a minimum of 2 feet", "residential-interior-design", "123"),
    ("average table manufacture allows 24 inches per person", "id-reference-spec", "96"),
    ("clearance space of 36 inches around beds wheelchairs", "residential-interior-design", "167"),
    ("furniture clearances bedroom not less than", "time-saver-interior", "87"),
    ("recommended light levels kitchen foot-candles lux", "id-reference-spec", "219"),
    ("best shading device for south windows continues to be the overhang", "lechner-hcl",
     "15.5 SHADING IN TROPICAL CLIMATES"),
]


def _index_ready():
    if not k.DB.is_file():
        raise unittest.SkipTest("knowledge index not built on this machine (scripts/knowledge.py build)")
    books = {s["id"] for s in k.stats()}
    missing = {b for _, b, _ in GOLDEN} - books
    if missing:
        raise unittest.SkipTest("books not indexed here: " + ", ".join(sorted(missing)))


class GoldenTests(unittest.TestCase):
    def setUp(self):
        _index_ready()

    def test_known_answers_in_top_five_with_citable_page(self):
        for query, book, where in GOLDEN:
            hits = k.search(query, limit=5)
            ok = [h for h in hits if h["book"] == book and
                  (h["printed_page"] == where or where in (h["section"] or ""))]
            self.assertTrue(ok, f"{query!r}: expected {book} {where}, got "
                                f"{[(h['book'], h['printed_page']) for h in hits]}")

    def test_nonsense_returns_nothing(self):
        self.assertEqual(k.search("xylophonic quasar marmalade"), [])

    def test_epub_is_cited_by_section_never_page(self):
        h = k.search("best shading device for south windows", book="lechner-hcl", limit=1)[0]
        self.assertTrue(h["cite"].startswith("section"))

    def test_dictionary_resolves_index_terms_to_pages(self):
        hits = k.lookup_term("kitchens layouts")
        self.assertTrue(any(h["book"] == "neufert" and h["pdf_pages"] for h in hits))

    def test_unreliable_numbering_is_labelled(self):
        basis = {s["id"]: s["label_basis"] for s in k.stats()}
        self.assertTrue(basis["construction-illustrated"].startswith("printed chapter-page"))
        self.assertIn("UNRELIABLE", basis["problem-seeking"])


class LabelTests(unittest.TestCase):
    """Page-number logic on synthetic pages (runs everywhere)."""

    def test_chapter_page_tokens_and_hex_labels(self):
        self.assertIn("5.45", k._edge_tokens("WOOD STUD FRAMING   5.45\nbody text"))
        self.assertIn("15-11", k._edge_tokens("Auditoria 15-11\nbody"))
        self.assertEqual(k._decode_label("<FEFF003400370030002D>1"), "470-1")

    def test_back_index_splits_several_entries_on_one_line(self):
        texts = ["body"] * 9 + ["Index\nPrams: spaces for movement 19, storage space 74\nKitchens, layouts 56, 57"]
        labels = [str(i) for i in range(10)]
        terms = {e["term"]: e["refs"] for e in k.back_index(texts, labels)}
        self.assertEqual(terms.get("Prams, spaces for movement"), "19")
        self.assertIn("Prams, storage space", terms)
        self.assertEqual(terms.get("Kitchens, layouts"), "56, 57")


if __name__ == "__main__":
    unittest.main()
