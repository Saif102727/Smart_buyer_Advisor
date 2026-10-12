"""Immutable configuration: app settings + per-country market profiles."""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CountryProfile:
    name: str
    flag: str
    currency: str
    currency_words: tuple[str, ...]
    stores: tuple[str, ...]
    trust: dict
    sales_seasons: str
    region: str = "xa-ar"


COUNTRIES: dict[str, CountryProfile] = {
    "مصر": CountryProfile(
        "مصر", "🇪🇬", "EGP", ("جنيه", "ج.م", "egp", "l.e", "le"),
        ("amazon.eg", "noon.com", "jumia.com.eg", "btech.com", "2b.com.eg", "olx.com.eg"),
        {"amazon.eg": .9, "noon.com": .85, "jumia.com.eg": .75, "btech.com": .9, "2b.com.eg": .85, "olx.com.eg": .4},
        "رمضان • وايت فرايداي (نوفمبر) • العودة للمدارس"),
    "السعودية": CountryProfile(
        "السعودية", "🇸🇦", "SAR", ("ريال", "ر.س", "sar", "sr"),
        ("amazon.sa", "noon.com", "extra.com", "jarir.com", "sa.opensooq.com"),
        {"amazon.sa": .9, "noon.com": .85, "extra.com": .9, "jarir.com": .9, "sa.opensooq.com": .4},
        "اليوم الوطني • يوم التأسيس • وايت فرايداي"),
    "الإمارات": CountryProfile(
        "الإمارات", "🇦🇪", "AED", ("درهم", "د.إ", "aed"),
        ("amazon.ae", "noon.com", "sharafdg.com", "dubizzle.com"),
        {"amazon.ae": .9, "noon.com": .85, "sharafdg.com": .9, "dubizzle.com": .4},
        "DSF • وايت فرايداي • 11.11"),
    "أمريكا": CountryProfile(
        "أمريكا", "🇺🇸", "USD", ("$", "usd"),
        ("amazon.com", "bestbuy.com", "walmart.com", "newegg.com", "ebay.com"),
        {"amazon.com": .9, "bestbuy.com": .9, "walmart.com": .85, "newegg.com": .8, "ebay.com": .6},
        "Prime Day • Black Friday • Cyber Monday", region="us-en"),
}


@dataclass(frozen=True, slots=True)
class Settings:
    max_product_len: int = 80
    max_extra_len: int = 60
    max_budget: float = 10_000_000
    search_per_session: int = 6          # عمليات بحث لكل جلسة
    search_global: int = 60              # عمليات بحث لكل التطبيق
    report_per_session: int = 3
    report_global: int = 20
    rate_period_s: int = 600
    login_attempts: int = 5
    cache_ttl_s: int = 900
    history_retention_days: int = 180
    search_timeout_s: int = 10
    max_workers: int = 4
    db_path: str = "data/price_history.db"
    model_dir: str = "models"
    llm_model: str = "claude-sonnet-5-5"
    access_code: str = ""                # فارغ = بدون بوابة دخول

    @classmethod
    def from_env(cls) -> "Settings":
        d, e = cls(), os.environ.get          # d = القيم الافتراضية (لا تُقرأ من الكلاس لأن slots=True تحذفها)
        return cls(
            db_path=e("SMARTBUYER_DB", d.db_path),
            model_dir=e("SMARTBUYER_MODEL_DIR", d.model_dir),
            llm_model=e("SMARTBUYER_LLM_MODEL", d.llm_model),
            access_code=e("SMARTBUYER_ACCESS_CODE", d.access_code),
        )
