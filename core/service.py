"""منسّق البحث (Facade): يجمع العروض والمراجعات والبدائل ويحسب الدرجات — بدون أي اعتماد على Streamlit."""
from __future__ import annotations

import threading
import time
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

import pandas as pd

from .config import COUNTRIES, CountryProfile, Settings
from .errors import RateLimitError, ResearchError
from .logs import get_logger
from .models import Alternative, ResearchRequest, ResearchResult, SearchHit
from .parsing import PriceParser, RatingParser
from .scoring import ValueScorer
from .search import SearchProvider
from .security import SlidingWindowRateLimiter
from .sentiment import SentimentAnalyzer
from .storage import PriceRepository

log = get_logger("service")


class TTLCache:
    def __init__(self, ttl: float, maxsize: int = 128):
        self._ttl, self._max = ttl, maxsize
        self._d: "OrderedDict[tuple, tuple[float, ResearchResult]]" = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key):
        with self._lock:
            item = self._d.get(key)
            if item and time.monotonic() - item[0] < self._ttl:
                return item[1]
            self._d.pop(key, None)
            return None

    def set(self, key, value):
        with self._lock:
            self._d[key] = (time.monotonic(), value)
            while len(self._d) > self._max:
                self._d.popitem(last=False)


class ResearchService:
    def __init__(self, settings: Settings, provider: SearchProvider, scorer: ValueScorer, repo: PriceRepository,
                 analyzer: SentimentAnalyzer, session_limiter: SlidingWindowRateLimiter, global_limiter: SlidingWindowRateLimiter):
        self._s, self._provider, self._scorer, self._repo = settings, provider, scorer, repo
        self._analyzer, self._sl, self._gl = analyzer, session_limiter, global_limiter
        self._cache = TTLCache(settings.cache_ttl_s)

    @property
    def analyzer_name(self) -> str:
        return self._analyzer.name

    def history(self, product: str, country: str) -> pd.DataFrame:
        return self._repo.history(product, country)

    # ------------------------------------------------------------ الواجهة العامة
    def research(self, req: ResearchRequest, client_id: str) -> ResearchResult:
        cached = self._cache.get(req.cache_key())
        if cached is not None:
            return cached
        for limiter, key in ((self._sl, client_id), (self._gl, "global")):
            wait = limiter.acquire(key)
            if wait:
                raise RateLimitError(wait)
        profile = COUNTRIES[req.country]
        try:
            hits = self._run(self._plan(req, profile))
        except Exception as exc:                 # noqa: BLE001
            log.error("research failed: %s", type(exc).__name__)
            raise ResearchError() from exc

        offers = self._build_offers(hits["offer"], profile)
        if req.budget:
            offers = offers[offers["price"] <= req.budget].reset_index(drop=True)
        reviews = self._unique_text(hits["review"], 20)
        sentiment = self._analyzer.score(reviews)
        offers = self._scorer.score(offers, sentiment, req.price_weight)
        pros, cons = self._analyzer.pros_cons(reviews)
        result = ResearchResult(req, profile.currency, offers, reviews, self._alternatives(hits["alt"]),
                                sentiment, pros, cons, self._analyzer.name)
        self._repo.save(req.product, req.country, offers)
        self._cache.set(req.cache_key(), result)
        return result

    # ------------------------------------------------------------ داخلي
    @staticmethod
    def _plan(req: ResearchRequest, p: CountryProfile) -> list[tuple[str, str, str]]:
        base = f"{req.product} {req.extra}".strip()
        plan = [("offer", f"{base} site:{s}", p.region) for s in p.stores]
        plan += [("offer", f"سعر {base} في {p.name}", p.region), ("offer", f"{base} price {p.currency}", p.region)]
        plan += [("review", f"مراجعة {base} عيوب ومميزات", "wt-wt"), ("review", f"{base} review problems", "wt-wt"),
                 ("review", f"{base} تجربتي بعد الاستخدام", "wt-wt")]
        plan += [("alt", f"أفضل بدائل {req.product}", "wt-wt"), ("alt", f"best alternatives to {req.product}", "wt-wt")]
        return plan

    def _run(self, plan) -> dict[str, list[SearchHit]]:
        out: dict[str, list[SearchHit]] = {"offer": [], "review": [], "alt": []}
        with ThreadPoolExecutor(max_workers=self._s.max_workers) as pool:
            futures = [(tag, pool.submit(self._provider.search, q, max_results=8, region=reg)) for tag, q, reg in plan]
            for tag, f in futures:
                try:
                    out[tag] += f.result(timeout=self._s.search_timeout_s * 3)
                except Exception as exc:         # noqa: BLE001 — فشل استعلام واحد لا يُسقط البحث كله
                    log.warning("query failed: %s", type(exc).__name__)
        return out

    @staticmethod
    def _trust(host: str, profile: CountryProfile) -> float:
        return next((v for d, v in profile.trust.items() if host == d or host.endswith("." + d)), 0.5)

    def _build_offers(self, hits: list[SearchHit], profile: CountryProfile) -> pd.DataFrame:
        parser, seen, rows = PriceParser(profile.currency_words), set(), []
        for h in hits:
            if h.url in seen:
                continue
            seen.add(h.url)
            blob = f"{h.title} {h.body}"
            prices = parser.prices(blob)
            if not prices:
                continue
            host = (urlparse(h.url).hostname or "").lower().removeprefix("www.")
            rows.append(dict(store=host, title=h.title[:120], price=prices[0], rating=RatingParser.rating(blob),
                             url=h.url, trust=self._trust(host, profile), currency=profile.currency))
        df = pd.DataFrame(rows, columns=["store", "title", "price", "rating", "url", "trust", "currency"])
        if df.empty:
            return df
        med = df["price"].median()                # استبعاد الإكسسوارات وأخطاء الاستخراج
        return df[(df["price"] > 0.35 * med) & (df["price"] < 3 * med)].head(40).reset_index(drop=True)

    @staticmethod
    def _unique_text(hits: list[SearchHit], limit: int) -> list[str]:
        seen, out = set(), []
        for h in hits:
            t = f"{h.title}. {h.body}".strip()
            if t not in seen:
                seen.add(t)
                out.append(t)
        return out[:limit]

    @staticmethod
    def _alternatives(hits: list[SearchHit]) -> list[Alternative]:
        seen, out = set(), []
        for h in hits:
            if h.url not in seen:
                seen.add(h.url)
                out.append(Alternative(h.title, h.body, h.url))
        return out[:8]
