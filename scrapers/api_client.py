import random
from urllib.parse import quote
from bs4 import BeautifulSoup

from core.http_client import HTTPClient
from core.config import BASE_URL

def unique_id():
    parts = ''.join(format(random.randint(0, 0xFFFF), '04x') for _ in range(4))
    return parts + str(random.randint(4584, 4584 + 5828365))

class APIClient:
    def __init__(self, http_client: HTTPClient):
        self.http = http_client

    def check_user_ls(self, tokens: dict, referer: str, use_bh: bool = False) -> str:
        """Fetch the LS token from /Verification/check_user endpoint."""
        safe_ref = quote(referer, safe=':/')
        book_hash = tokens.get('b_h', '') if use_bh else ''
        
        resp = self.http.post(
            f"{BASE_URL}/Verification/check_user",
            data={
                'csrf_token': tokens.get('csrf_token', ''),
                'book_hash': book_hash,
                '_': tokens.get('crypto_token', ''),
                'ls': '', 'o': unique_id(),
            },
            headers={
                'Referer': safe_ref, 'Origin': BASE_URL,
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-Requested-With': 'XMLHttpRequest',
            }
        )
        if getattr(resp, 'status_code', None) == 200:
            try:
                return resp.json().get('ls', '')
            except:
                pass
        return ""

    def get_download_links(self, ls_token: str, tokens: dict, referer: str) -> dict:
        """Fetch the read and download links from the endpoint."""
        safe_ref = quote(referer, safe=':/')
        resp = self.http.post(
            f"{BASE_URL}/book/get_download_links?o={unique_id()}",
            data={
                'csrf_token': tokens.get('csrf_token', ''),
                'book_hash': tokens.get('book_hash', ''),
                '_': tokens.get('crypto_token', ''),
                'ls': ls_token, 
            },
            headers={
                'Referer': safe_ref, 'Origin': BASE_URL,
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-Requested-With': 'XMLHttpRequest',
            }
        )
        
        links = {'download_link': '', 'read_link': '', 'downloads': '', 'all_download_links': []}
        if getattr(resp, 'status_code', None) == 200:
            dl_soup = BeautifulSoup(resp.text, 'lxml')
            for a in dl_soup.find_all('a', href=True):
                href = a['href']
                if 'internal_download' in href:
                    full_link = BASE_URL + href if href.startswith('/') else href
                    
                    if not links['download_link']:
                        links['download_link'] = full_link
                    links['all_download_links'].append(full_link)
                    
                    if a.find('span') and not links['downloads']:
                        links['downloads'] = a.find_all('span')[-1].get_text(strip=True)
                        
                if '/book/read' in href or 'read-book' in href:
                    links['read_link'] = BASE_URL + href if href.startswith('/') else href
        return links
