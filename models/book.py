from dataclasses import dataclass
from typing import Optional

@dataclass
class BookDetails:
    url: str
    title: str
    author: Optional[str] = ""
    cover_image: Optional[str] = ""
    description: Optional[str] = ""
    ratings: Optional[str] = ""
    downloads: Optional[str] = ""
    download_links: Optional[str] = ""
    drive_links: Optional[str] = ""
    read_link: Optional[str] = ""
    qr_code: Optional[str] = ""
    category: Optional[str] = ""
    language: Optional[str] = ""
    pages: Optional[str] = ""
    file_size: Optional[str] = ""
    file_type: Optional[str] = ""
    creation_date: Optional[str] = ""
    other_tags: Optional[str] = ""
