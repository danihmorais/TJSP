import functools
import io
import json
import tempfile
import threading
import unittest
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from pypdf import PdfReader
from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass


class LegislationBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tempdir = tempfile.TemporaryDirectory()
        site = Path(cls.tempdir.name)
        (site / "data").mkdir()
        (site / "legislacao.html").write_text(
            (ROOT / "legislacao.html").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        data = {
            "generatedAt": "2026-11-20T00:00:00+00:00",
            "referenceDate": "2026-11-20",
            "documents": [
                {
                    "id": "cp",
                    "title": "Código Penal — Decreto-Lei nº 2.848/1940",
                    "discipline": "Direito Penal",
                    "group": "penal",
                    "source": "https://www.planalto.gov.br/ccivil_03/decreto-lei/del2848compilado.htm",
                    "updated": "Fonte oficial",
                    "headings": [{"id": "h-cp-1", "text": "TÍTULO I — DA APLICAÇÃO DA LEI PENAL", "level": "TÍTULO"}],
                    "articles": [
                        {
                            "number": 5,
                            "suffix": "",
                            "label": "Art. 5",
                            "body": "Art. 5º Aplica-se a lei brasileira, sem prejuízo de convenções, tratados e regras de direito internacional.",
                        },
                        {
                            "number": 6,
                            "suffix": "",
                            "label": "Art. 6",
                            "body": "Art. 6º Considera-se praticado o crime no lugar em que ocorreu a ação ou omissão.",
                        },
                    ],
                },
                {
                    "id": "cpp",
                    "title": "Código de Processo Penal — Decreto-Lei nº 3.689/1941",
                    "discipline": "Direito Processual Penal",
                    "group": "processo-penal",
                    "source": "https://www.planalto.gov.br/ccivil_03/decreto-lei/del3689compilado.htm",
                    "updated": "Fonte oficial",
                    "headings": [{"id": "h-cpp-1", "text": "TÍTULO I — DO PROCESSO EM GERAL", "level": "TÍTULO"}],
                    "articles": [
                        {
                            "number": 1,
                            "suffix": "",
                            "label": "Art. 1",
                            "body": "Art. 1º O processo penal reger-se-á, em todo o território brasileiro, por este Código.",
                        },
                    ],
                },
            ],
        }
        (site / "data" / "legislacao.json").write_text(
            json.dumps(data, ensure_ascii=False),
            encoding="utf-8",
        )
        handler = functools.partial(QuietHandler, directory=str(site))
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f"http://127.0.0.1:{cls.server.server_port}/legislacao.html"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)
        cls.tempdir.cleanup()

    def read_pdf(self, page, mode, button, target_texts, excluded_texts=()):
        page.emulate_media(media="screen")
        page.evaluate("resetPrintState()")
        page.locator(button).click()
        page.wait_for_function(
            "document.body.classList.contains('print-all') || document.body.classList.contains('print-mode')"
        )
        page.emulate_media(media="print")
        pdf = page.pdf(prefer_css_page_size=True, print_background=True)
        reader = PdfReader(io.BytesIO(pdf))
        texts = [(item.extract_text() or "").strip() for item in reader.pages]
        self.assertGreaterEqual(len(texts), 2)
        self.assertIn("SUMÁRIO", texts[0])
        self.assertTrue(all(text for text in texts), "A impressão contém página sem texto.")
        full_text = "\n".join(texts)
        for expected in target_texts:
            self.assertIn(expected, full_text)
            self.assertIn(expected, texts[0] if mode == "toc" else full_text)
        for excluded in excluded_texts:
            self.assertNotIn(excluded, full_text)
        return texts

    def test_screen_search_and_all_group_document_print_modes(self):
        page_errors = []
        console_errors = []
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context()
            context.add_init_script("window.print = () => {};")
            page = context.new_page()
            page.on("pageerror", lambda error: page_errors.append(str(error)))
            page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
            response = page.goto(self.url, wait_until="networkidle")
            self.assertEqual(response.status, 200)
            page.wait_for_function(
                "document.querySelector('#status').hidden && document.querySelectorAll('.document').length === 2"
            )
            title_color = page.locator("#doc-cp h2").evaluate("(el) => getComputedStyle(el).color")
            self.assertNotEqual(title_color, "rgb(255, 255, 255)")
            page.locator("#search").fill("lei brasileira")
            self.assertTrue(page.locator("#doc-cp").is_visible())
            self.assertFalse(page.locator("#doc-cpp").is_visible())
            page.locator("#clear").click()
            self.assertTrue(page.locator("#doc-cpp").is_visible())

            all_texts = self.read_pdf(

                page,
                "all",
                "#print-all",
                ["DIREITO PENAL", "DIREITO PROCESSUAL PENAL", "Código Penal", "Código de Processo Penal"],
            )
            title_pages = {
                "Código Penal": next(i for i, text in enumerate(all_texts[1:], start=1) if "Código Penal" in text),
                "Código de Processo Penal": next(
                    i for i, text in enumerate(all_texts[1:], start=1) if "Código de Processo Penal" in text
                ),
            }
            self.assertNotEqual(title_pages["Código Penal"], title_pages["Código de Processo Penal"])

            group_texts = self.read_pdf(

                page,
                "group",
                '[data-print="group"][data-target="penal"]',
                ["Código Penal"],
                ["Código de Processo Penal"],
            )
            self.assertIn("Código Penal", group_texts[0])

            document_texts = self.read_pdf(

                page,
                "document",
                '[data-print="doc"][data-target="cp"]',
                ["TÍTULO I — DA APLICAÇÃO DA LEI PENAL"],
                ["Código de Processo Penal"],
            )
            self.assertIn("SUMÁRIO", document_texts[0])
            self.assertIn("Art. 5º", "\n".join(document_texts))
            self.assertFalse(page_errors, "\n".join(page_errors))
            self.assertFalse(console_errors, "\n".join(console_errors))
            context.close()
            browser.close()


if __name__ == "__main__":
    unittest.main()
