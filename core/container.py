"""Composition Root: المكان الوحيد الذي تُركَّب فيه الكائنات (Dependency Injection يدوي)."""
from __future__ import annotations

import os
from dataclasses import dataclass

from .config import Settings
from .report import ReportService
from .scoring import ValueScorer
from .search import DuckDuckGoProvider
from .security import AccessGate, InputValidator, SlidingWindowRateLimiter
from .sentiment import SentimentFactory
from .service import ResearchService
from .storage import PriceRepository


@dataclass(frozen=True)
class Container:
    settings: Settings
    validator: InputValidator
    research: ResearchService
    reports: ReportService
    gate: AccessGate

    @classmethod
    def build(cls, settings: Settings | None = None, server_key: str | None = None) -> "Container":
        s = settings or Settings.from_env()
        rl = lambda n: SlidingWindowRateLimiter(n, s.rate_period_s)       # noqa: E731
        research = ResearchService(
            s, DuckDuckGoProvider(s.search_timeout_s), ValueScorer(),
            PriceRepository(s.db_path, s.history_retention_days),
            SentimentFactory(s.model_dir).create(), rl(s.search_per_session), rl(s.search_global))
        reports = ReportService(s.llm_model, rl(s.report_per_session), rl(s.report_global),
                                server_key or os.environ.get("ANTHROPIC_API_KEY"))
        gate = AccessGate(s, SlidingWindowRateLimiter(s.login_attempts, 900))
        return cls(s, InputValidator(s), research, reports, gate)
