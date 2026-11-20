import importlib.util
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("build_legislacao", ROOT / "scripts" / "build_legislacao.py")
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)


class HtmlExtractionTests(unittest.TestCase):
    def test_inline_tags_do_not_split_paragraph_or_create_false_article(self):
        source = """
        <html><body>
        <p>Art. 5º Todos são <b>iguais</b> perante a lei, <a href="#">(Redação dada pela Lei nº 1)</a> sem distinção.</p>
        <p>§ 1º O disposto no <a href="#">art. 3º</a> aplica-se.</p>
        <p>Art. 6º Outro dispositivo.</p>
        </body></html>
        """
        spec = {"title": "Teste", "minimum": 2, "ranges": [(5, 6)], "exact": []}
        blocks = builder.legal_blocks(source, "teste")
        records = builder.extract_html_articles(spec, source, blocks)
        self.assertEqual([record["number"] for record in records], [5, 6])
        self.assertTrue(records[0]["body"].startswith("Art. 5º"))
        self.assertIn("iguais perante a lei", records[0]["body"])
        self.assertIn("(Redação dada pela Lei nº 1)", records[0]["body"])
        self.assertNotIn("Art. 3", [record["label"] for record in records])

    def test_leaf_div_is_extracted_without_splitting_inline_markup(self):
        source = """
        <html><body>
        <div class="artigo">Art. 25. Texto em <strong>bloco div</strong> da fonte.</div>
        <div class="artigo">Art. 26. Próximo artigo.</div>
        </body></html>
        """
        spec = {"title": "Teste", "minimum": 2, "ranges": [(25, 26)], "exact": []}
        blocks = builder.legal_blocks(source, "teste")
        records = builder.extract_html_articles(spec, source, blocks)
        self.assertEqual([record["number"] for record in records], [25, 26])
        self.assertIn("bloco div", records[0]["body"])

    def test_br_splits_only_at_structural_boundaries(self):
        source = """
        <html><body>
        <p>TÍTULO I<br>Art. 25. Texto inicial<br>continuação do mesmo parágrafo.</p>
        </body></html>
        """
        blocks = builder.legal_blocks(source, "br")
        self.assertEqual(len(blocks), 2)
        self.assertEqual(blocks[0]["text"], "TÍTULO I")
        self.assertTrue(blocks[1]["isArticle"])
        self.assertIn("continuação do mesmo parágrafo", blocks[1]["text"])
        spec = {"title": "Teste", "minimum": 1, "ranges": [(25, 25)], "exact": []}
        records = builder.extract_html_articles(spec, source, blocks)
        self.assertTrue(records[0]["body"].startswith("Art. 25."))

    def test_br_inside_paragraph_remains_a_space(self):
        source = "<body><p>Art. 5º Texto inicial<br>continuação sem novo artigo.</p></body>"
        blocks = builder.legal_blocks(source)
        self.assertEqual(len(blocks), 1)
        self.assertIn("Texto inicial continuação", blocks[0]["text"])

    def test_table_with_paragraph_is_emitted_once(self):
        source = "<html><body><table><tr><td><p>Texto único</p></td></tr></table></body></html>"
        blocks = builder.legal_blocks(source)
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0]["text"], "Texto único")

    def test_table_without_paragraph_keeps_table_markup(self):
        source = "<html><body><table><tr><td>Texto da tabela</td></tr></table></body></html>"
        blocks = builder.legal_blocks(source)
        self.assertEqual(len(blocks), 1)
        self.assertIn("<table", blocks[0]["html"])
        self.assertIn("Texto da tabela", blocks[0]["text"])

    def test_structural_heading_has_stable_id(self):
        blocks = builder.legal_blocks("<body><p>TÍTULO I</p><p>Art. 1º Texto.</p></body>", "codigo")
        headings = builder.headings_from_blocks(blocks)
        self.assertEqual(headings[0]["id"], "h-codigo-1")
        self.assertEqual(headings[0]["text"], "TÍTULO I")


class PdfExtractionTests(unittest.TestCase):
    def test_pdf_lines_are_reflowed_and_repeated_headers_removed(self):
        pages = [
            ["CABEÇALHO OFICIAL", "Art. 1º O texto começa na", "primeira linha e termina em hí-"],
            ["CABEÇALHO OFICIAL", "fen.", "§ 1º O parágrafo seguinte.", "2"],
        ]
        paragraphs = builder.reflow_pdf_pages(pages)
        self.assertEqual(len(paragraphs), 2)
        self.assertEqual(paragraphs[0], "Art. 1º O texto começa na primeira linha e termina em hífen.")
        self.assertEqual(paragraphs[1], "§ 1º O parágrafo seguinte.")

    def test_article_prefix_is_preserved(self):
        records = builder.parse_articles("Art. 5º Texto do artigo.\n§ 1º Complemento.\nArt. 6º Outro texto.")
        self.assertEqual(len(records), 2)
        self.assertTrue(records[0]["body"].startswith("Art. 5º"))
        self.assertIn("§ 1º Complemento.", records[0]["body"])


class FallbackTests(unittest.TestCase):
    def test_previous_document_is_reused_and_marked_stale(self):
        with tempfile.TemporaryDirectory() as directory:
            previous_out = builder.OUT
            previous_sources = builder.SOURCES
            try:
                builder.OUT = Path(directory) / "legislacao.json"
                builder.SOURCES = {"teste": {"title": "Documento de teste"}}
                builder.OUT.write_text(json.dumps({
                    "documents": [{"id": "teste", "title": "Documento anterior", "articles": []}]
                }), encoding="utf-8")
                with patch.object(builder, "build_document", side_effect=RuntimeError("timeout")):
                    with redirect_stdout(StringIO()):
                        builder.main()
                payload = json.loads(builder.OUT.read_text(encoding="utf-8"))
                self.assertEqual(len(payload["documents"]), 1)
                self.assertTrue(payload["documents"][0]["stale"])
                self.assertEqual(payload["documents"][0]["error"], "timeout")
            finally:
                builder.OUT = previous_out
                builder.SOURCES = previous_sources

    def test_missing_new_and_previous_version_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            previous_out = builder.OUT
            previous_sources = builder.SOURCES
            try:
                builder.OUT = Path(directory) / "missing.json"
                builder.SOURCES = {"teste": {"title": "Documento de teste"}}
                with patch.object(builder, "build_document", side_effect=RuntimeError("indisponível")):
                    with self.assertRaises(RuntimeError):
                        builder.main()
                self.assertFalse(builder.OUT.exists())
            finally:
                builder.OUT = previous_out
                builder.SOURCES = previous_sources


if __name__ == "__main__":
    unittest.main()
