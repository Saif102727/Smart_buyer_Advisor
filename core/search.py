"""مزوّدو البحث. الواجهة المجردة تسمح باستبدال DuckDuckGo بـ SerpAPI/Keepa دون تغيير باقي النظام."""
from __future__ import annotations

import time
from abc import ABC, abstractmethod

from .logs import get_logger
from .models import SearchHit
from .security import TextSanitizer, UrlPolicy

log = get_logger("search")


class SearchProvider(ABC):
    @abstractmethod
    def search(self, query: str, *, max_results: int = 8, region: str = "wt-wt") -> list[SearchHit]:
        """يرجع نتائج معقّمة: نصوص بلا HTML وروابط http(s) آمنة فقط."""


class DuckDuckGoProvider(SearchProvider):
    def __init__(self, timeout: int = 10, retries: int = 2):
        self._timeout, self._retries = timeout, retries

    def search(self, query: str, *, max_results: int = 8, region: str = "wt-wt") -> list[SearchHit]:
        try:
            from ddgs import DDGS
        except ImportError:                                  # الاسم القديم للمكتبة
            from duckduckgo_search import DDGS
        for attempt in range(self._retries + 1):
            try:
                with DDGS(timeout=self._timeout) as d:
                    raw = d.text(query, region=region, max_results=max_results) or []
                return self._clean(raw)
            except Exception as exc:                         # noqa: BLE001 — لا نعرض التفاصيل للمستخدم
                log.warning("search attempt %d failed: %s", attempt + 1, type(exc).__name__)
                time.sleep(0.6 * (attempt + 1))
        return []

    @staticmethod
    def _clean(raw: list[dict]) -> list[SearchHit]:
        hits = []
        for r in raw:
            url = str(r.get("href") or "").strip()
            if not UrlPolicy.is_safe(url):
                continue
            hits.append(SearchHit(TextSanitizer.clean(r.get("title"), 160), url, TextSanitizer.clean(r.get("body"), 400)))
        return hits
