import time
import os
from curl_cffi.requests import Session as CfSession
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from rich.progress import Progress, BarColumn, TextColumn, DownloadColumn, TransferSpeedColumn

from core.config import get_random_user_agent, TIMEOUT, CHUNK_SIZE
from core.logger import logger

class HTTPClientError(Exception):
    pass

class HTTPClient:
    def __init__(self):
        self._session = CfSession(impersonate="chrome110")
        self._session.headers.update({
            'User-Agent': get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'ar,en-US;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        logger.info("[dim]🌐 Initialized HTTP Session (Chrome TLS)[/dim]")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((HTTPClientError, Exception))
    )
    def get(self, url: str) -> str:
        """Make a GET request with exponential backoff for 403s and errors."""
        try:
            resp = self._session.get(url, timeout=TIMEOUT, allow_redirects=True)
            if resp.status_code == 200:
                logger.debug(f"GET 200 - {url}")
                return resp.text
            elif resp.status_code == 403:
                logger.warning(f"⚠️ 403 Forbidden - {url}")
                raise HTTPClientError(f"HTTP 403 from {url}")
            else:
                logger.warning(f"⚠️ HTTP {resp.status_code} - {url}")
                raise HTTPClientError(f"HTTP {resp.status_code} from {url}")
        except Exception as e:
            if not isinstance(e, HTTPClientError):
                logger.error(f"Request error GET {url}: {str(e)}")
            raise

    def post(self, url: str, data: dict, headers: dict = None) -> object:
        """Make a POST request without aggressive retries for token APIs."""
        try:
            resp = self._session.post(
                url, data=data, timeout=TIMEOUT,
                allow_redirects=True, headers=headers or {}
            )
            return resp
        except Exception as e:
            logger.error(f"POST error to {url}: {str(e)}")
            return None

    def download(self, url: str, filepath: str, timeout: int = 600) -> bool:
        """Download a file with progress bar."""
        try:
            resp = self._session.get(url, timeout=timeout, allow_redirects=True, stream=True)
            if resp.status_code == 200:
                total_size = int(resp.headers.get('content-length', 0))
                
                with Progress(
                    TextColumn("[cyan]Downloading..."),
                    BarColumn(),
                    DownloadColumn(),
                    TransferSpeedColumn(),
                ) as progress:
                    task = progress.add_task("download", total=total_size or None)
                    with open(filepath, 'wb') as f:
                        for chunk in resp.iter_content(chunk_size=CHUNK_SIZE):
                            if chunk:
                                f.write(chunk)
                                progress.update(task, advance=len(chunk))
                return True
            else:
                logger.error(f"  ✗ HTTP {resp.status_code} for download {url}")
        except Exception as e:
            logger.error(f"  ✗ Download error for {url}: {str(e)}")
        return False

    def close(self):
        if self._session:
            self._session.close()
            self._session = None
            logger.debug("[dim]Session closed[/dim]")
