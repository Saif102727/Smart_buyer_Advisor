"""Domain objects (immutable where possible)."""
from __future__ import annotations

import time
from dataclasses import dataclass, field

import pandas as pd


@dataclass(frozen=True, slots=True)
class SearchHit:
    title: str
    url: str
    body: str


@dataclass(frozen=True, slots=True)
class Alternative:
    title: str
    body: str
    url: str


@dataclass(frozen=True, slots=True)
class ResearchRequest:
    product: str
    country: str
    extra: str = ""
    budget: float = 0.0
    price_weight: float = 0.5

    def cache_key(self) -> tuple:
        return (self.product.casefold(), self.country, self.extra.casefold(), round(self.budget), round(self.price_weight, 2))


@dataclass(slots=True)
class ResearchResult:
    request: ResearchRequest
    currency: str
    offers: pd.DataFrame
    reviews: list[str]
    alternatives: list[Alternative]
    sentiment: float
    pros: int = 0
    cons: int = 0
    analyzer: str = "lexicon"
    created_at: float = field(default_factory=time.time)

    @property
    def allowed_urls(self) -> set[str]:
        urls = set(self.offers["url"]) if not self.offers.empty else set()
        return urls | {a.url for a in self.alternatives}
