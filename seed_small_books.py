import os
import sys
import time
from bs4 import BeautifulSoup
from core.http_client import HTTPClient
from core.database import Database
from parsers.book_parser import BookParser
from parsers.text_utils import extract_tokens
from scrapers.api_client import APIClient

try:
    if os.path.exists('noor_book.db'):
        os.remove('noor_book.db')
except PermissionError:
    import sqlite3
    c = sqlite3.connect('noor_book.db')
    for table in ['books', 'temp_books', 'authors', 'temp_authors']:
        c.execute(f"DROP TABLE IF EXISTS {table}")
    c.commit()
    c.close()

db = Database()
client = HTTPClient()
api_client = APIClient(client)

print("Fetching authors...")
html = client.get("https://www.noor-book.com/مؤلفو-الكتب")
tokens = extract_tokens(html)
csrf = tokens.get('csrf_token')
ls = api_client.check_user_ls(tokens, "https://www.noor-book.com/مؤلفو-الكتب")

soup = BeautifulSoup(html, 'lxml')
authors = []
for a in soup.select('div.row.book_rows > div a[href]'):
    href = a['href']
    if href.startswith('/'): href = "https://www.noor-book.com" + href
    if 'كتب' in href:
        authors.append(href)

books_added = 0
for author_url in set(authors):
    if books_added >= 3: break
    print(f"\nScanning author: {author_url}")
    a_html = client.get(author_url)
    a_soup = BeautifulSoup(a_html, 'lxml')
    book_links = []
    for a in a_soup.select('div.row.book_rows a.img-a'):
        b_href = a['href']
        if b_href.startswith('/'): b_href = "https://www.noor-book.com" + b_href
        book_links.append(b_href)
        
    for b_url in book_links:
        if books_added >= 3: break
        try:
            b_html = client.get(b_url)
            details = BookParser.parse_book_details(b_html, b_url)
            size = 0
            if details.file_size:
                try:
                    size = float(details.file_size)
                except ValueError:
                    pass
            if 0 < size <= 5.0:
                print(f"✅ Found small book: {details.title} (Size: {size})")
                db.add_temp_books([b_url])
                books_added += 1
            else:
                pass # print(f"❌ Skipping ({size} MB)")
        except Exception as e:
            pass

print(f"\nSuccessfully queued {books_added} small books.")
