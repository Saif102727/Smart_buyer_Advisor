import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from streamlit.testing.v1 import AppTest

from core.config import Settings
from core.container import Container
from core.errors import RateLimitError
from core.models import ResearchRequest, SearchHit
from core.search import SearchProvider


class FakeProvider(SearchProvider):
    def search(self, query, *, max_results=8, region="wt-wt"):
        if "site:amazon.eg" in query:
            return [SearchHit("Galaxy A55 256GB - Amazon.eg", "https://www.amazon.eg/dp/1", "السعر 18,999 جنيه تقييم 4.6 من 5")]
        if "site:noon.com" in query:
            return [SearchHit("Galaxy A55 | noon", "https://www.noon.com/p/2", "EGP 17,500 شحن مجاني"),
                    SearchHit("حافظة Galaxy A55", "https://www.noon.com/p/3", "EGP 150")]       # إكسسوار ← يُستبعد
        if "review" in query or "مراجعة" in query or "تجربتي" in query:
            return [SearchHit("مراجعة A55", "https://r.com/1", "هاتف ممتاز وسريع جدا لكن البطارية متوسطة")]
        if "بدائل" in query or "alternatives" in query:
            return [SearchHit("أفضل بدائل", "https://alt.com/1", "Pixel 8a وiPhone 15")]
        return [SearchHit("سعر Galaxy", "https://x.com/9", "نبيع بـ 19,200 ج.م مع ضمان")]


@pytest.fixture
def container(tmp_path):
    s = Settings(db_path=str(tmp_path / "p.db"), model_dir=str(tmp_path / "m"), search_per_session=2)
    c = Container.build(s)
    object.__setattr__(c.research, "_provider", FakeProvider())
    return c


def test_research_end_to_end(container):
    r = container.research.research(ResearchRequest("Galaxy A55", "مصر", price_weight=0.5), "u1")
    assert not r.offers.empty
    assert 150 not in set(r.offers["price"])                 # الإكسسوار مُستبعد
    assert r.offers["price"].min() == 17500 and r.offers.iloc[0]["value_score"] >= r.offers.iloc[-1]["value_score"]
    assert 0 <= r.sentiment <= 1 and r.alternatives
    assert not container.research.history("Galaxy A55", "مصر").empty


def test_cache_and_rate_limit(container):
    req = lambda n: ResearchRequest(f"Galaxy A{n}", "مصر")
    container.research.research(req(1), "u1")
    container.research.research(req(1), "u1")                # من الكاش ← لا يستهلك الحد
    container.research.research(req(2), "u1")
    with pytest.raises(RateLimitError):
        container.research.research(req(3), "u1")


def test_ui_renders_results(container):
    r = container.research.research(ResearchRequest("Galaxy A55", "مصر"), "u2")
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30)
    at.session_state["result"] = r
    at.run()
    assert not at.exception, at.exception
