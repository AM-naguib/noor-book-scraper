# Noor-Book Scraper (Refactored & Automated)

A robust, production-ready Python CLI scraper for fetching author profiles and books from Noor-Book.
It bypasses anti-bot measures, downloads detailed book metadata, processes multi-part books, automatically uploads books to Google Drive, downloads book covers locally, and manages the entire state seamlessly via an SQLite database.

## 🚀 Key Improvements & Features
* **Isolated HTTP Client**: Wraps `curl_cffi` to mimic Chrome TLS fingerprints and bypass Cloudflare.
* **Auto Retries & Backoff**: Uses `tenacity` for resilience against 403s and network interruptions.
* **Separation of Concerns**: Beautiful Soup Parsing, HTTP Networking, and Orchestration logic are separated.
* **Google Drive Uploading (Streaming)**: Streams books directly from Noor-Book to your Google Drive account without consuming local disk space.
* **Smart Folder Organization**: Automatically organizes books into folders on Google Drive (e.g., folder `1` for books 1-1000, `2` for 1001-2000).
* **Local Cover Archiving**: Downloads and saves high-quality book covers locally to speed up your website.
* **Multi-part Books**: Easily handles books that are split into dozens of parts (e.g. Encyclopedia PDF parts).
* **Configurable Data Layer**: SQLite state tracking ensures you can interrupt and resume scanning without data loss.

---

## 🏗️ Architecture Overview

The system uses a decoupled layout, separating data models, fetching, and parsing.

```text
noorbook_scraper/
├── README.md               <-- Documentation
├── .env                    <-- Environment variables 
├── .env.example            <-- Env vars template
├── requirements.txt
├── main.py                 <-- CLI Entrypoint
├── core/
│   ├── config.py           <-- Centralized .env and app settings
│   ├── database.py         <-- SQLite interface and queries
│   ├── http_client.py      <-- curl_cffi wrapper with tenacity retries
│   └── logger.py           <-- Rich formatted logging singleton
├── models/
│   ├── author.py           <-- Dataclasses for Author
│   └── book.py             <-- Dataclasses for Book
├── parsers/
│   ├── book_parser.py      <-- BeautifulSoup HTML extraction purely in memory
│   └── text_utils.py       <-- Regex extractors for Javascript payload tokens
└── scrapers/
    ├── api_client.py       <-- Logic for requesting inner Noor-Book API links
    └── orchestrator.py     <-- Pipeline combining HTTP + Parsers + Data Saves
```

---

## ⚙️ Setup and Installation

**1. Install Dependencies**
```bash
pip install -r requirements.txt
```

**2. Setup Environment Variables**
Copy `.env.example` to `.env` and adjust the variables.
```bash
cp .env.example .env
```

*Example `.env`:*
```ini
BASE_URL="https://www.noor-book.com"
DB_PATH="noor_book.db"

MIN_DELAY=2.0
MAX_DELAY=5.0
MAX_RETRIES=3
TIMEOUT=30
DRIVE_ROOT_FOLDER_ID="YOUR_GOOGLE_DRIVE_FOLDER_ID"
```

---

## ☁️ Google Drive Setup (One-Time)
Before running the scraper to upload files, you need to authenticate it with your Google Drive:
1. Make sure you have your `credentials.json` file in the root directory (from Google Cloud Console -> Desktop App).
2. Run the setup script:
```bash
python setup_drive.py
```
3. A browser window will open. Login with your Google account and grant the requested permissions.
4. The script will generate a `token.json` file. You will never need to login again.

---

## 🛠️ Run Commands

The scraping logic is batched into 3 distinct commands. Run them consecutively or in parallel across different terminals if desired. The database maintains state synchronization automatically.

**1. Crawl Author Pages (Queueing)**
```bash
# Standard mode: Crawl sequentially
python main.py

# Concurrent mode 🚀 (Extremely Fast): Crawl pages concurrently
# -c or --concurrent: Enable concurrent fetching
# -w or --workers: Number of simultaneous connections (Default: 20)
# -p or --max-pages: Number of pages to fetch (Default: 100)
python main.py --concurrent --max-pages 100 --workers 15
```
> **⚠️ Warning for Concurrent Mode**: It is highly recommended to keep `--workers` (or `-w`) at `15` or `20` maximum. Using a higher number (like 50) may trigger Cloudflare's bot protection or cause "Operation timed out" errors (`curl: 28`) because the server will refuse to serve too many requests at the exact same time.

**2. Scrape Author Details & Find Books**
```bash
# Parses profile info and extracts links to their books into temp_books
python main.py --crawl-details --limit 100
```

**3. Scrape Final Book Details & Upload to Drive**
```bash
# Fetch details. If you add --download, it will download covers locally and upload PDFs to Google Drive.
python main.py --crawl-books --limit 100 --download
```

**📊 Show Stats & Queue Counters**
```bash
python main.py --info
```

---

## 🗑️ Problems Found & Solutions Applied

| Found Problem | Solution Applied |
|:---|:---|
| **God Class `Crawler`** | The crawler class was almost 500 lines long, mingling SQL code, generic python logic, bs4 parsing, requests, token grabbing, and string manipulation. Broke logic into 6 dedicated services across `scrapers/`, `core/`, and `parsers/`. |
| **Token Checking Redundancies** | Extracted into `api_client.check_user_ls` and `text_utils.extract_tokens`. Prevents repeating 4 duplicate logic loops. |
| **Silent Failures** | Wrapped networking using standard Python `logging` customized with `RichHandler` for readable terminal outputs. Removed basic `time.sleep` loops in favor of `tenacity` exponential backoff to handle rate limits perfectly. |
| **Un-Typed Dictionaries** | Replaced mutable, unchecked dictionary data with Python `@dataclasses` schemas under the `models/` directory for robust mapping. |
| **Spaghetti Globals** | Centralized global variables and path generation into `core/config.py` backed by `python-dotenv`. |
