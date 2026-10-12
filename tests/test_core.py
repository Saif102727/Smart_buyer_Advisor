import json
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.config import Settings
from core.errors import ValidationError
from core.parsing import PriceParser, RatingParser
from core.scoring import ValueScorer
from core.security import (InputValidator, ModelIntegrity, SlidingWindowRateLimiter, TextSanitizer, UrlPolicy, csv_safe)
from core.sentiment import LexiconAnalyzer, lexicon_polarity


# ---------- الأسعار
@pytest.fixture
def eg():
    return PriceParser(("جنيه", "ج.م", "egp", "l.e", "le"))


def test_price_basic(eg):
    assert eg.prices("سعر الموبايل 12,999 جنيه فقط") == [12999.0]
    assert eg.prices("EGP 8500") == [8500.0]
    assert eg.prices("٢٥٬٠٠٠ جنيه") == [25000.0]


def test_price_ignores_installments_and_word_fragments(eg):
    assert eg.prices("قسط 500 جنيه شهريا") == [] or eg.prices("500 جنيه شهريا") == []
    assert eg.prices("5 leather sofa") == []          # "le" داخل كلمة


def test_rating():
    assert RatingParser.rating("تقييم 4.5 من 5") == 4.5
    assert RatingParser.rating("rated 4/5 stars") == 4.0
    assert RatingParser.rating("9 من 10") is None


# ---------- الأمان
def test_url_policy():
    assert UrlPolicy.is_safe("https://www.amazon.eg/dp/123")
    for bad in ["javascript:alert(1)", "data:text/html,x", "http://localhost/x", "http://127.0.0.1/x",
                "http://192.168.1.5/", "https://user:pw@evil.com/", "ftp://x.com", "https://a.com/ b", ""]:
        assert not UrlPolicy.is_safe(bad), bad


def test_sanitizer_strips_html_and_escapes():
    assert "<" not in TextSanitizer.clean("<script>alert(1)</script>سعر &lt;b&gt;جيد&lt;/b&gt;")
    assert TextSanitizer.escape('"><img src=x onerror=alert(1)>') == "&quot;&gt;&lt;img src=x onerror=alert(1)&gt;"


def test_markdown_blocks_images_and_foreign_links():
    md = "![t](https://evil.com/p.png?d=secret) [x](javascript:alert(1)) [ok](https://a.com/p) https://evil.com/q <b>x</b>"
    out = TextSanitizer.markdown(md, {"https://a.com/p"})
    assert "evil.com" not in out and "javascript" not in out and "<b>" not in out and "![" not in out
    assert "[ok](https://a.com/p)" in out


def test_validator():
    v = InputValidator(Settings())
    assert v.product("  iPhone   15  ") == "iPhone 15"
    assert v.product("site:evil.com laptop") == "laptop"
    for bad in ["", "a", "x" * 500, "<script>", "laptop; DROP TABLE prices;--"]:
        with pytest.raises(ValidationError):
            v.product(bad)
    assert v.product("lap\u202etop") == "lap top"        # محارف Bidi الخفية تُزال
    with pytest.raises(ValidationError):
        v.budget("abc")
    with pytest.raises(ValidationError):
        v.budget(float("nan"))
    with pytest.raises(ValidationError):
        v.country("Atlantis")


def test_rate_limiter():
    t = [0.0]
    rl = SlidingWindowRateLimiter(2, 10, clock=lambda: t[0])
    assert rl.acquire("a") == 0 and rl.acquire("a") == 0
    assert rl.acquire("a") > 0 and rl.acquire("b") == 0
    t[0] = 11
    assert rl.acquire("a") == 0


def test_csv_injection():
    out = csv_safe(pd.DataFrame({"t": ["=HYPERLINK(1)", "+1", "ok"], "p": [1, 2, 3]}))
    assert list(out["t"]) == ["'=HYPERLINK(1)", "'+1", "ok"]


def test_model_integrity(tmp_path):
    f = tmp_path / "m.joblib"
    f.write_bytes(b"model-bytes")
    mi = ModelIntegrity(tmp_path)
    assert not mi.verify(f)                 # لا بصمة مسجلة ← مرفوض
    mi.register(f)
    assert mi.verify(f)
    f.write_bytes(b"tampered")
    assert not mi.verify(f)


# ---------- التقييم والمشاعر
def test_scoring_prefers_value():
    df = pd.DataFrame({"store": ["a", "b"], "title": ["x", "y"], "price": [100.0, 110.0], "rating": [3.0, 4.8],
                       "url": ["u1", "u2"], "trust": [0.4, 0.9], "currency": ["EGP"] * 2})
    out = ValueScorer().score(df, 0.7, 0.4)
    assert out.iloc[0]["store"] == "b" and {"value_score", "vs_median_pct"} <= set(out.columns)


def test_lexicon():
    assert lexicon_polarity("منتج ممتاز وسريع") > 0
    assert lexicon_polarity("سيء ومشاكل كثيرة") < 0
    assert lexicon_polarity("لا أنصح به") < 0
    assert 0 <= LexiconAnalyzer().score(["رائع", "سيء"]) <= 1


def test_settings_from_env_defaults(monkeypatch):
    for k in ("SMARTBUYER_DB", "SMARTBUYER_MODEL_DIR", "SMARTBUYER_LLM_MODEL", "SMARTBUYER_ACCESS_CODE"):
        monkeypatch.delenv(k, raising=False)
    s = Settings.from_env()
    assert s.db_path == "data/price_history.db" and s.model_dir == "models" and isinstance(s.llm_model, str)
    assert s.access_code == ""
