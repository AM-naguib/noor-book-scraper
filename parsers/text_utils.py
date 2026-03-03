import re
from typing import Dict

def extract_tokens(html: str) -> Dict[str, str]:
    """Extract standard javascript payload tokens for authentication barriers."""
    tokens = {}
    patterns = {
        'csrf_token': r"var\s+csrf_token\s*=\s*'([^']+)'",
        'crypto_token': r"var\s+crypto_token\s*=\s*'([^']+)'",
        'book_hash': r"var\s+book_hash\s*=\s*'([^']+)'",
        'b_h': r"var\s+b_h\s*=\s*'([^']+)'",
    }
    for key, pattern in patterns.items():
        m = re.search(pattern, html)
        if m:
            tokens[key] = m.group(1)
    return tokens

def sanitize_filename(name: str) -> str:
    """Sanitize a string for use as a filename."""
    # Remove invalid filename characters
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '', name)
    # Replace multiple spaces/dots
    name = re.sub(r'\s+', ' ', name).strip()
    name = re.sub(r'\.{2,}', '.', name)
    # Trim to reasonable length
    if len(name) > 200:
        name = name[:200]
    return name or 'unnamed_book'
