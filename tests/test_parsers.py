import unittest
from parsers.text_utils import extract_tokens
from parsers.book_parser import BookParser

class TestParsers(unittest.TestCase):
    def test_extract_tokens(self):
        html = """
        <script>
        var csrf_token = 'abc123csrf';
        var crypto_token = 'def456crypto';
        var book_hash = 'hash789book';
        </script>
        """
        tokens = extract_tokens(html)
        self.assertEqual(tokens.get('csrf_token'), 'abc123csrf')
        self.assertEqual(tokens.get('crypto_token'), 'def456crypto')
        self.assertEqual(tokens.get('book_hash'), 'hash789book')

    def test_parse_book_details_empty(self):
        html = "<html><body></body></html>"
        book = BookParser.parse_book_details(html, "http://example.com/book1")
        self.assertEqual(book.url, "http://example.com/book1")
        self.assertEqual(book.title, "")
        self.assertEqual(book.description, "")

if __name__ == '__main__':
    unittest.main()
