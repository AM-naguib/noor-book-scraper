import sqlite3
from pathlib import Path
from core.config import DB_PATH
from models.author import AuthorDetails, AuthorBase
from models.book import BookDetails
from typing import List, Dict, Any

class Database:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS temp_authors (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, url TEXT UNIQUE NOT NULL, crawled INTEGER DEFAULT 0, created_at TEXT DEFAULT CURRENT_TIMESTAMP)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS authors (
            id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, name TEXT, url TEXT UNIQUE NOT NULL, image TEXT, description TEXT, avg_rate TEXT, rate TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS temp_books (
            id INTEGER PRIMARY KEY AUTOINCREMENT, url TEXT UNIQUE NOT NULL, crawled INTEGER DEFAULT 0, created_at TEXT DEFAULT CURRENT_TIMESTAMP)''')
        try:
            cursor.execute("ALTER TABLE temp_books ADD COLUMN crawled INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass
        cursor.execute('''CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT, url TEXT UNIQUE NOT NULL, title TEXT, author TEXT, cover_image TEXT, description TEXT, ratings TEXT, downloads TEXT, download_links TEXT, drive_links TEXT, read_link TEXT, qr_code TEXT, category TEXT, language TEXT, pages TEXT, file_size TEXT, file_type TEXT, creation_date TEXT, other_tags TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP)''')
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_temp_authors_url ON temp_authors(url)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_authors_url ON authors(url)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_temp_books_url ON temp_books(url)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_books_url ON books(url)")
        conn.commit()
        conn.close()

    def add_temp_authors(self, authors: List[AuthorBase]):
        conn = self._get_conn()
        try:
            conn.executemany("INSERT OR IGNORE INTO temp_authors (name, url) VALUES (?, ?)", [(a.name, a.url) for a in authors])
            conn.commit()
        finally:
            conn.close()

    def add_temp_books(self, book_urls: List[str]):
        conn = self._get_conn()
        try:
            conn.executemany("INSERT OR IGNORE INTO temp_books (url) VALUES (?)", [(url,) for url in book_urls])
            conn.commit()
        finally:
            conn.close()

    def add_author(self, author: AuthorDetails):
        conn = self._get_conn()
        try:
            conn.execute('''INSERT OR REPLACE INTO authors (title, name, url, image, description, avg_rate, rate) VALUES (?, ?, ?, ?, ?, ?, ?)''', 
                         (author.title, author.name, author.url, author.image, author.description, author.avg_rate, author.rate))
            conn.commit()
        finally:
            conn.close()

    def add_book(self, book: BookDetails) -> int:
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute('''INSERT OR REPLACE INTO books (url, title, author, cover_image, description, ratings, downloads, download_links, drive_links, read_link, qr_code, category, language, pages, file_size, file_type, creation_date, other_tags) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                         (book.url, book.title, book.author, book.cover_image, book.description, book.ratings, book.downloads, book.download_links, book.drive_links, book.read_link, book.qr_code, book.category, book.language, book.pages, book.file_size, book.file_type, book.creation_date, book.other_tags))
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def update_book_drive_links(self, book_id: int, drive_links_json: str):
        conn = self._get_conn()
        try:
            conn.execute("UPDATE books SET drive_links = ? WHERE id = ?", (drive_links_json, book_id))
            conn.commit()
        finally:
            conn.close()

    def get_pending_temp_authors(self, limit: int = 100) -> List[Dict[str, Any]]:
        conn = self._get_conn()
        try:
            rows = conn.execute("SELECT * FROM temp_authors WHERE crawled = 0 LIMIT ?", (limit,)).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def get_pending_temp_books(self, limit: int = 100) -> List[Dict[str, Any]]:
        conn = self._get_conn()
        try:
            rows = conn.execute("SELECT * FROM temp_books WHERE crawled = 0 LIMIT ?", (limit,)).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def mark_temp_author_crawled(self, url: str):
        conn = self._get_conn()
        try:
            conn.execute("UPDATE temp_authors SET crawled = 1 WHERE url = ?", (url,))
            conn.commit()
        finally:
            conn.close()

    def mark_temp_book_crawled(self, url: str):
        conn = self._get_conn()
        try:
            conn.execute("UPDATE temp_books SET crawled = 1 WHERE url = ?", (url,))
            conn.commit()
        finally:
            conn.close()

    def get_stats(self) -> Dict[str, int]:
        conn = self._get_conn()
        try:
            total_temp = conn.execute("SELECT COUNT(*) FROM temp_authors").fetchone()[0]
            crawled_temp = conn.execute("SELECT COUNT(*) FROM temp_authors WHERE crawled = 1").fetchone()[0]
            authors_count = conn.execute("SELECT COUNT(*) FROM authors").fetchone()[0]
            total_books_temp = conn.execute("SELECT COUNT(*) FROM temp_books").fetchone()[0]
            crawled_books_temp = conn.execute("SELECT COUNT(*) FROM temp_books WHERE crawled = 1").fetchone()[0]
            books_count = conn.execute("SELECT COUNT(*) FROM books").fetchone()[0]
            return {
                'total_queue': total_temp,
                'crawled_queue': crawled_temp,
                'pending_queue': total_temp - crawled_temp,
                'authors_final': authors_count,
                'total_books_temp': total_books_temp,
                'crawled_books_temp': crawled_books_temp,
                'pending_books_temp': total_books_temp - crawled_books_temp,
                'books_final': books_count
            }
        finally:
            conn.close()
