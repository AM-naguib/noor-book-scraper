import os
import json
import time
import concurrent.futures
import threading
from bs4 import BeautifulSoup

from core.http_client import HTTPClient
from core.database import Database
from core.logger import logger
from core.drive_client import DriveClient
from core.drive_client import DriveClient
from core.config import BASE_URL, get_random_delay, MAX_PAGES_PER_TAG, DOWNLOAD_DIR, COVERS_DIR
from models.author import AuthorBase
from scrapers.api_client import APIClient
from parsers.text_utils import extract_tokens, sanitize_filename
from parsers.book_parser import BookParser

class Orchestrator:
    def __init__(self, db: Database):
        self.db = db
        self.http_client = HTTPClient()
        self.api_client = APIClient(self.http_client)
        self.drive_client = DriveClient()

    def crawl_authors(self, max_pages: int = 0, start_page: int = 1):
        logger.info(f"[bold cyan]👤 Fetching Authors (Starting from page {start_page})...[/bold cyan]")
        base_authors_url = f"{BASE_URL}/مؤلفو-الكتب"
        page = start_page
        total_authors = 0
        
        html = self.http_client.get(base_authors_url)
        if not html:
            logger.error("⚠️ Failed to fetch initial authors page")
            return

        tokens = extract_tokens(html)
        csrf = tokens.get('csrf_token')
        ls = self.api_client.check_user_ls(tokens, base_authors_url) if csrf else None

        if not csrf or not ls:
            logger.error("❌ Failed to retrieve authentication tokens for pagination.")
            return
            
        is_first_iteration = True
        page_retries = 0
        
        while True:
            try:
                if page == 1 and is_first_iteration:
                    current_html = html
                else:
                    current_html = self.http_client.get(f"{base_authors_url}?page_ajax={page}&token={csrf}&ls={ls}")
                is_first_iteration = False
                page_retries = 0
            except Exception as e:
                page_retries += 1
                if page_retries > 3:
                    logger.error(f"❌ Maximum retries exceeded for page {page}. Exiting crawl.")
                    break
                logger.warning(f"⚠️ Failed fetching page {page} (Retry {page_retries}/3).")
                logger.info("🔄 Cooling down for 15 seconds and refreshing tokens...")
                time.sleep(15)
                try:
                    # Renew session and tokens to fix expiration/IP blocks
                    self.http_client.close()
                    self.http_client = HTTPClient()
                    self.api_client = APIClient(self.http_client)
                    
                    fresh_html = self.http_client.get(base_authors_url)
                    if fresh_html:
                        new_tokens = extract_tokens(fresh_html)
                        new_csrf = new_tokens.get('csrf_token')
                        new_ls = self.api_client.check_user_ls(new_tokens, base_authors_url) if new_csrf else None
                        if new_csrf and new_ls:
                            csrf = new_csrf
                            ls = new_ls
                            html = fresh_html
                            logger.info("[green]✅ Tokens & Browser Session refreshed successfully.[/green]")
                except Exception as inner_e:
                    logger.error(f"❌ Failed to refresh tokens: {inner_e}")
                
                continue
                
            if not current_html or len(current_html) < 200:
                logger.info(f"⚠️ No more content at page {page}")
                break
                
            soup = BeautifulSoup(current_html, 'lxml')
            author_divs = soup.select('div.row.book_rows > div')
            
            if not author_divs:
                break
                
            new_authors = []
            for div in author_divs:
                a_tag = div.select_one('a[href]')
                if not a_tag: continue
                href = a_tag['href']
                if href.startswith('/'): href = BASE_URL + href
                    
                title_tag = a_tag.find(['h2', 'h3', 'div'])
                name = title_tag.get_text(strip=True) if title_tag else a_tag.get_text(strip=True)
                new_authors.append(AuthorBase(name=name, url=href))
            
            if not new_authors: break
                
            newly_inserted = self.db.add_temp_authors(new_authors)
            total_authors += newly_inserted
            logger.info(f"[green]✓ Page {page}: Fetched {len(new_authors)} | New: {newly_inserted} (DB Added: {total_authors})[/green]")
                
            limit = max_pages if max_pages > 0 else MAX_PAGES_PER_TAG
            if limit > 0 and page >= limit: break
            page += 1
            time.sleep(get_random_delay())
            
    def crawl_authors_concurrent(self, max_pages: int = 0, max_workers: int = 20, start_page: int = 1):
        url_limit = max_pages
        logger.info(f"[bold cyan]👤 Fetching Authors Concurrently (Start: {start_page}, Max pages: {'Unlimited' if url_limit <= 0 else url_limit})...[/bold cyan]")
        base_authors_url = f"{BASE_URL}/مؤلفو-الكتب"
        
        html = self.http_client.get(base_authors_url)
        if not html:
            logger.error("⚠️ Failed to fetch initial authors page")
            return

        tokens = extract_tokens(html)
        csrf = tokens.get('csrf_token')
        ls = self.api_client.check_user_ls(tokens, base_authors_url) if csrf else None

        if not csrf or not ls:
            logger.error("❌ Failed to retrieve authentication tokens for pagination.")
            return

        total_authors = 0

        def fetch_page(page_num):
            url = f"{base_authors_url}?page_ajax={page_num}&token={csrf}&ls={ls}"
            try:
                current_html = self.http_client.get(url) 
                if not current_html or len(current_html) < 200:
                    return page_num, [], True

                soup = BeautifulSoup(current_html, 'lxml')
                author_divs = soup.select('div.row.book_rows > div')
                if not author_divs:
                    return page_num, [], True
                
                new_authors = []
                for div in author_divs:
                    a_tag = div.select_one('a[href]')
                    if not a_tag: continue
                    href = a_tag['href']
                    if href.startswith('/'): href = BASE_URL + href
                        
                    title_tag = a_tag.find(['h2', 'h3', 'div'])
                    name = title_tag.get_text(strip=True) if title_tag else a_tag.get_text(strip=True)
                    new_authors.append(AuthorBase(name=name, url=href))
                    
                return page_num, new_authors, False
            except Exception as e:
                logger.error(f"Error fetching page {page_num}: {e}")
                return page_num, [], False

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            current_page = start_page
            has_more_pages = True
            
            while has_more_pages:
                batch_size = max_workers
                if url_limit > 0:
                    remaining = (url_limit - current_page) + 1
                    if remaining <= 0:
                        break
                    batch_size = min(batch_size, remaining)
                
                batch_end = current_page + batch_size
                futures = {executor.submit(fetch_page, p): p for p in range(current_page, batch_end)}
                
                for future in concurrent.futures.as_completed(futures):
                    page_num, new_authors, is_end = future.result()
                    
                    if is_end:
                        has_more_pages = False
                        
                    if new_authors:
                        newly_inserted = self.db.add_temp_authors(new_authors)
                        total_authors += newly_inserted
                        if newly_inserted > 0:
                            logger.info(f"[green]✓ Page {page_num}: Fetched {len(new_authors)} | New: {newly_inserted} (New Total DB: {total_authors})[/green]")
                        else:
                            logger.info(f"[dim]✓ Page {page_num}: Fetched {len(new_authors)} | New: 0 (All Duplicates)[/dim]")
                
                current_page = batch_end

            
    def crawl_author_details(self, limit: int = 100):
        pending = self.db.get_pending_temp_authors(limit=limit)
        if not pending:
            logger.info("[yellow]ℹ️ No pending authors to crawl details for.[/yellow]")
            return

        logger.info(f"[bold cyan]🕵️ Crawling details for {len(pending)} authors...[/bold cyan]")
        for author in pending:
            url = author['url']
            try:
                html = self.http_client.get(url)
            except Exception:
                logger.error(f"[red]✗ Failed to fetch {url}[/red]")
                continue

            # Extract details
            author_details = BookParser.parse_author_details(html, url)
            self.db.add_author(author_details)
            self.db.mark_temp_author_crawled(url)
            logger.info(f"[green]✓ Saved Author: {author_details.name}[/green]")

            # Books Pagination
            tokens = extract_tokens(html)
            csrf = tokens.get('csrf_token')
            ls = self.api_client.check_user_ls(tokens, url) if csrf else None
            
            self._crawl_author_books_pagination(url, html, csrf, ls)
            time.sleep(get_random_delay())

        logger.info("[bold green]✅ Batch detail and book crawl finished.[/bold green]")

    def _crawl_author_books_pagination(self, author_url: str, initial_html: str, csrf: str, ls: str):
        logger.info(f"[cyan]📚 Extracting books...[/cyan]")
        author_books_count = 0
        book_page = 1
        
        while True:
            book_html = initial_html if book_page == 1 else self.http_client.get(f"{author_url}?page_ajax={book_page}&token={csrf}&ls={ls}")
            
            if not book_html or len(book_html) < 200:
                break
                
            book_soup = BeautifulSoup(book_html, 'lxml')
            book_links = []
            for a in book_soup.select('div.row.book_rows a.img-a'):
                book_url = a.get('href', '')
                if book_url:
                    if book_url.startswith('/'): book_url = BASE_URL + book_url
                    book_links.append(book_url)
            
            if not book_links: break
                
            self.db.add_temp_books(book_links)
            author_books_count += len(book_links)
            
            if len(book_links) < 20: break
            
            book_page += 1
            time.sleep(get_random_delay())
        
        logger.info(f"[green]✓ Found {author_books_count} books for this author.[/green]")

    def crawl_book_details(self, limit: int = 100, download_pdfs: bool = False):
        pending = self.db.get_pending_temp_books(limit=limit)
        if not pending:
            logger.info("[yellow]ℹ️ No pending books to crawl details for.[/yellow]")
            return

        logger.info(f"[bold cyan]🕵️ Crawling details for {len(pending)} books...[/bold cyan]")
        
        for book in pending:
            url = book['url']
            try:
                html = self.http_client.get(url)
            except Exception:
                logger.error(f"[red]✗ Failed to fetch {url}[/red]")
                self.db.mark_temp_book_crawled(url)
                continue

            book_details = BookParser.parse_book_details(html, url)
            
            # API Links
            tokens = extract_tokens(html)
            ls_token = self.api_client.check_user_ls(tokens, url, use_bh=True)
            if ls_token:
                links = self.api_client.get_download_links(ls_token, tokens, url)
                all_links = links.get('all_download_links', [])
                book_details.download_links = json.dumps(all_links, ensure_ascii=False)
                book_details.read_link = links.get('read_link', '')
                book_details.downloads = links.get('downloads', '')

            # Download Cover Image Locally
            if book_details.cover_image:
                cover_url = book_details.cover_image
                if cover_url.startswith('/'):
                    cover_url = BASE_URL + cover_url
                    
                if cover_url.startswith('http'):
                    os.makedirs(COVERS_DIR, exist_ok=True)
                    ext = cover_url.split('?')[0].split('.')[-1][:4] # handle params
                    if ext.lower() not in ['jpg', 'jpeg', 'png', 'webp', 'gif']:
                        ext = 'jpg'
                    safe_title_for_cover = sanitize_filename(book_details.title) if book_details.title else "Untitled"
                    cover_filename = f"{safe_title_for_cover}.{ext}"
                    cover_filepath = os.path.join(COVERS_DIR, cover_filename)
                    
                    if not os.path.exists(cover_filepath):
                        logger.info(f"[cyan]  🖼️ Downloading cover: {cover_filename}[/cyan]")
                        success = self.http_client.download(cover_url, cover_filepath)
                        if success:
                            book_details.cover_image = f"covers/{cover_filename}"
                    else:
                        book_details.cover_image = f"covers/{cover_filename}"

            book_id = self.db.add_book(book_details)
            self.db.mark_temp_book_crawled(url)
            title_display = book_details.title[:40] if book_details.title else "Untitled"
            logger.info(f"[green]✓ Saved Book: {title_display}...[/green]")

            if download_pdfs and all_links:
                drive_links = []
                for idx, link in enumerate(all_links, start=1):
                    safe_title = sanitize_filename(book_details.title)
                    suffix = f" (Part {idx})" if len(all_links) > 1 else ""
                    filename = f"{safe_title}{suffix}.pdf"
                    filepath = os.path.join(DOWNLOAD_DIR, filename)

                    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
                    logger.info(f"[cyan]  ⬇️ Downloading: {filename}[/cyan]")
                    success = self.http_client.download(link, filepath)
                    if success:
                        logger.info(f"[green]  ✅ Download complete! Uploading to Drive...[/green]")
                        try:
                            drive_link = self.drive_client.upload_file(filepath, filename, book_id)
                            if drive_link:
                                drive_links.append(drive_link)
                            logger.info(f"[green]  ✅ Upload complete! URL: {drive_link}[/green]")
                        except Exception as e:
                            logger.error(f"[red]  ❌ Upload failed: {e}[/red]")
                        finally:
                            if os.path.exists(filepath):
                                os.remove(filepath)
                                logger.info(f"[dim]  🗑️ Deleted local file: {filename}[/dim]")
                    else:
                        logger.error(f"[red]  ❌ Download failed for {filename}[/red]")
                    time.sleep(get_random_delay())
                
                if drive_links:
                    self.db.update_book_drive_links(book_id, json.dumps(drive_links, ensure_ascii=False))

            time.sleep(get_random_delay())

        logger.info("[bold green]✅ Batch book detail crawl finished.[/bold green]")

    def shutdown(self):
        self.http_client.close()
