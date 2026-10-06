import unittest
from unittest.mock import patch

from web_reader import (
    WebpageReadError,
    _ReadableHTML,
    read_requested_pages,
    requested_urls,
)


class WebReaderTests(unittest.TestCase):
    def test_requires_inspection_intent_except_for_bare_urls(self):
        self.assertEqual(
            requested_urls("Check this out: https://example.com"),
            ["https://example.com"],
        )
        self.assertEqual(requested_urls("https://example.com"), ["https://example.com"])
        self.assertEqual(
            requested_urls("What does this page say? https://example.com"),
            ["https://example.com"],
        )
        self.assertEqual(
            requested_urls("My profile mentions https://example.com but tell me about AWS"),
            [],
        )

    def test_inspection_instruction_applies_to_multiple_urls(self):
        self.assertEqual(
            requested_urls("Read these pages: https://one.example and https://two.example"),
            ["https://one.example", "https://two.example"],
        )

    def test_extracts_readable_html_without_navigation_or_script(self):
        parser = _ReadableHTML()
        parser.feed(
            "<html><head><title>Example article</title></head><body>"
            "<nav>Home Menu</nav><main><article><h1>Useful heading</h1>"
            "<p>Readable <strong>page</strong> text.</p><script>ads()</script>"
            "<ul><li>First point</li><li>Second point</li></ul>"
            "</article></main></body></html>"
        )
        title, content = parser.result()
        self.assertEqual(title, "Example article")
        self.assertIn("Useful heading", content)
        self.assertIn("Readable page text.", content)
        self.assertIn("• First point", content)
        self.assertNotIn("Home Menu", content)
        self.assertNotIn("ads()", content)

    def test_returns_separate_temporary_context_and_surfaces_read_failures(self):
        with patch(
            "web_reader._read_page",
            return_value=("Example", "Page contents", "https://example.com/"),
        ):
            context, was_read = read_requested_pages("Summarise this: https://example.com")
        self.assertTrue(was_read)
        self.assertIn("User's original request", context)
        self.assertIn("Summarise this: https://example.com", context)
        self.assertIn("Temporary webpage content", context)
        self.assertIn("Page contents", context)

        with patch("web_reader._read_page", side_effect=WebpageReadError("timed out")):
            with self.assertRaisesRegex(WebpageReadError, "couldn't read.*timed out"):
                read_requested_pages("Read this: https://example.com")


if __name__ == "__main__":
    unittest.main()