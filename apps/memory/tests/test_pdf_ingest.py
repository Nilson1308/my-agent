from __future__ import annotations

from django.test import SimpleTestCase

from apps.memory.pdf_ingest import chunk_text


class PdfChunkTests(SimpleTestCase):
    def test_chunk_short(self) -> None:
        self.assertEqual(chunk_text("uma frase só"), ["uma frase só"])

    def test_chunk_splits_long_text(self) -> None:
        text = "parágrafo. " * 500
        chunks = chunk_text(text, max_chars=400, overlap=50)
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(c) <= 420 for c in chunks))