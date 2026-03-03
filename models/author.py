from dataclasses import dataclass
from typing import Optional

@dataclass
class AuthorBase:
    name: str
    url: str

@dataclass
class AuthorDetails(AuthorBase):
    title: str
    image: str
    description: str
    avg_rate: str
    rate: str
