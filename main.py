import argparse
import sys
import os

from core.database import Database
from core.logger import logger
from scrapers.orchestrator import Orchestrator
from rich.table import Table

# Setup UTF-8 for Windows Console
os.environ['PYTHONIOENCODING'] = 'utf-8'
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

def show_stats(db: Database):
    stats = db.get_stats()
    table = Table(title="📊 Statistics", border_style="cyan")
    table.add_column("Metric", style="bold")
    table.add_column("Value", justify="right", style="green")
    table.add_row("Total Authors in Queue", str(stats.get('total_queue', 0)))
    table.add_row("Crawled Authors in Queue", str(stats.get('crawled_queue', 0)))
    table.add_row("Pending Authors in Queue", str(stats.get('pending_queue', 0)))
    table.add_row("Final Authors Table", str(stats.get('authors_final', 0)))
    table.add_section()
    table.add_row("Total Books in Queue", str(stats.get('total_books_temp', 0)))
    table.add_row("Crawled Books in Queue", str(stats.get('crawled_books_temp', 0)))
    table.add_row("Pending Books in Queue", str(stats.get('pending_books_temp', 0)))
    table.add_row("Final Books Table", str(stats.get('books_final', 0)))
    
    from rich.console import Console
    Console().print(table)

def main():
    parser = argparse.ArgumentParser(description="Noor-Book Authors Scraper (Refactored)")
    parser.add_argument('--max-pages', '-p', type=int, default=0, help='Max pages to crawl list')
    parser.add_argument('--crawl-details', '-d', action='store_true', help='Crawl author profiles from queue')
    parser.add_argument('--crawl-books', '-b', action='store_true', help='Crawl book details from queue')
    parser.add_argument('--download', action='store_true', help='Download the PDF files when crawling books')
    parser.add_argument('--limit', '-l', type=int, default=50, help='Limit for crawl-details or crawl-books')
    parser.add_argument('--info', '-i', action='store_true', help='Show stats')
    parser.add_argument('--concurrent', '-c', action='store_true', help='Use concurrent mode to fetch authors')
    parser.add_argument('--workers', '-w', type=int, default=20, help='Max workers for concurrent mode')
    args = parser.parse_args()

    logger.info("[bold cyan]📚 Noor-Book Authors Scraper[/bold cyan]")
    db = Database()

    if args.info:
        show_stats(db)
        return

    orchestrator = None
    try:
        orchestrator = Orchestrator(db)
        
        if args.crawl_details:
            orchestrator.crawl_author_details(limit=args.limit)
        elif args.crawl_books:
            orchestrator.crawl_book_details(limit=args.limit, download_pdfs=args.download)
        elif args.concurrent:
            orchestrator.crawl_authors_concurrent(max_pages=args.max_pages, max_workers=args.workers)
        else:
            orchestrator.crawl_authors(max_pages=args.max_pages)
            
        show_stats(db)

    except KeyboardInterrupt:
        logger.warning("⚠️ Interrupted by user.")
        show_stats(db)
    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=False)
    finally:
        if orchestrator:
            orchestrator.shutdown()

if __name__ == '__main__':
    main()
