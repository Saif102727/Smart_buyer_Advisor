"""طبقة العرض (Streamlit) مبنية بـ OOP: SessionStore / SidebarView / ResultsView / SmartBuyerApp."""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import streamlit as st
from streamlit.runtime.scriptrunner import get_script_run_ctx

from core.config import COUNTRIES
from core.container import Container
from core.errors import SmartBuyerError
from core.logs import get_logger
from core.models import ResearchRequest, ResearchResult
from core.security import UrlPolicy, csv_safe
from core.sentiment import lexicon_polarity
from ui.charts import ChartFactory
from ui.components import Components
from ui.theme import ThemeManager

log = get_logger("ui")


@st.cache_resource(show_spinner=False)
def get_container() -> Container:
    """كائن واحد مشترك بين الجلسات (النماذج، الكاش، وحدود المعدل العامة)."""
    try:
        server_key = st.secrets.get("ANTHROPIC_API_KEY")
    except Exception:                                  # لا يوجد ملف secrets
        server_key = None
    return Container.build(server_key=server_key)


def client_id() -> str:
    ctx = get_script_run_ctx()
    return ctx.session_id if ctx else "anonymous"


class SessionStore:
    """غلاف مُنمَّط حول st.session_state (لا نخزّن مفاتيح API هنا أبداً)."""

    def __init__(self):
        self._s = st.session_state

    result = property(lambda s: s._s.get("result"), lambda s, v: s._s.__setitem__("result", v))
    report = property(lambda s: s._s.get("report"), lambda s, v: s._s.__setitem__("report", v))
    authed = property(lambda s: s._s.get("authed", False), lambda s, v: s._s.__setitem__("authed", v))


@dataclass(frozen=True)
class SearchForm:
    product: str
    country: str
    extra: str
    budget: float
    weight: float


class SidebarView:
    def __init__(self, c: Container):
        self._c = c

    def render(self) -> SearchForm | None:
        with st.sidebar:
            st.html('<div class="side-brand"><div class="mark">ص</div><div><b>مستشار الشراء</b>'
                    '<small>قارن • اختر • وفّر</small></div></div>')
            with st.form("search", border=False):
                product = st.text_input("المنتج", max_chars=self._c.settings.max_product_len,
                                        placeholder="مثال: Samsung Galaxy A55")
                country = st.selectbox("الدولة", list(COUNTRIES), format_func=lambda n: f"{COUNTRIES[n].flag}  {n}")
                extra = st.text_input("كلمات إضافية", max_chars=self._c.settings.max_extra_len, placeholder="256GB، ضمان وكيل")
                budget = st.number_input("الميزانية القصوى (0 = بدون حد)", 0, int(self._c.settings.max_budget), 0, 500)
                weight = st.slider("الأولوية", 0.0, 1.0, 0.5, 0.05, help="يمين: السعر الأرخص أهم • يسار: الجودة أهم")
                st.caption("◀ جودة أعلى          سعر أقل ▶")
                go = st.form_submit_button("ابحث عن أفضل عرض", type="primary", width="stretch")
            st.caption(f"محلل المراجعات: {self._c.research.analyzer_name}")
        return SearchForm(product, country, extra, budget, weight) if go else None


class ResultsView:
    def __init__(self, c: Container, store: SessionStore):
        self._c, self._store = c, store

    def render(self, r: ResearchResult) -> None:
        offers, cur = r.offers, r.currency
        if offers.empty:
            st.html(Components.error("لم نجد أسعاراً واضحة. جرّب اسماً أدق للمنتج أو ارفع الميزانية."))
            return
        cheapest = offers.loc[offers["price"].idxmin()]
        best = offers.iloc[0]
        median = offers["price"].median()
        st.html(Components.stats([
            ("أرخص سعر", f"{cheapest.price:,.0f}", cur, cheapest.store, "hibiscus"),
            ("أفضل قيمة", f"{best.price:,.0f}", cur, best.store, "mint"),
            ("متوسط السوق", f"{median:,.0f}", cur, f"من {len(offers)} عرضاً", "lagoon"),
            ("الفارق بين الأرخص والأفضل", f"{abs(best.price - cheapest.price):,.0f}", cur, "ما تدفعه مقابل جودة أعلى", "saffron"),
        ]))
        gap = (median - cheapest.price) / median * 100
        st.html(Components.section("الصورة العامة") + Components.gauges(r.sentiment, float(best.value_score), [
            f"أرخص عرض أقل من متوسط السوق بنحو {gap:.0f}%.",
            f"أفضل قيمة: {best.store}.",
            f"مؤشرات إيجابية {r.pros} مقابل سلبية {r.cons} في المراجعات.",
        ]))

        st.html(Components.section("أفضل ثلاثة عروض", "مرتبة حسب القيمة"))
        picks = self._picks(offers)
        for col, (label, kind, row) in zip(st.columns(len(picks)), picks):
            with col:
                st.html(Components.ticket(label, kind, row, cur))
                if UrlPolicy.is_safe(row["url"]):
                    st.link_button("افتح العرض", row["url"], width="stretch")

        tabs = st.tabs(["📊 المقارنة", "🤖 التقرير الذكي", "💬 المراجعات", "🔄 البدائل", "📈 تاريخ الأسعار"])
        with tabs[0]:
            self._compare(r)
        with tabs[1]:
            self._report(r)
        with tabs[2]:
            self._reviews(r)
        with tabs[3]:
            self._alternatives(r)
        with tabs[4]:
            self._history(r)
        st.html(Components.footer())

    # ------------------------------------------------------------ أقسام
    @staticmethod
    def _picks(offers: pd.DataFrame) -> list[tuple[str, str, pd.Series]]:
        wanted = [("أفضل قيمة", "best", offers.iloc[0]),
                  ("الأرخص", "cheap", offers.loc[offers["price"].idxmin()]),
                  ("الأكثر أماناً", "safe", offers.sort_values(["trust", "value_score"], ascending=False).iloc[0])]
        seen, out = set(), []
        for label, kind, row in wanted:
            if row["url"] not in seen:
                seen.add(row["url"])
                out.append((label, kind, row))
        for _, row in offers.iterrows():                       # أكمل حتى 3 بطاقات مختلفة
            if len(out) >= min(3, len(offers)):
                break
            if row["url"] not in seen:
                seen.add(row["url"])
                out.append(("بديل جيد", "alt", row))
        return out

    def _compare(self, r: ResearchResult) -> None:
        a, b = st.columns(2)
        a.plotly_chart(ChartFactory.value_scatter(r.offers, r.currency), width="stretch", config={"displayModeBar": False})
        b.plotly_chart(ChartFactory.price_bars(r.offers, r.currency), width="stretch", config={"displayModeBar": False})
        table = r.offers[["store", "title", "price", "rating", "trust", "value_score", "url"]]
        st.dataframe(table, hide_index=True, width="stretch", column_config={
            "store": "المتجر", "title": "العنوان", "price": st.column_config.NumberColumn("السعر", format="%.0f"),
            "rating": "التقييم", "trust": st.column_config.ProgressColumn("الثقة", min_value=0, max_value=1),
            "value_score": st.column_config.ProgressColumn("القيمة", min_value=0, max_value=1),
            "url": st.column_config.LinkColumn("الرابط", display_text="فتح")})
        st.download_button("⬇️ تحميل CSV", csv_safe(table).to_csv(index=False).encode("utf-8-sig"), "offers.csv", "text/csv")
        st.caption(f"💡 مواسم التخفيضات: {COUNTRIES[r.request.country].sales_seasons}")

    def _report(self, r: ResearchResult) -> None:
        st.caption("يُرسَل ملخص النتائج فقط إلى النموذج اللغوي. مفتاحك لا يُسجَّل ولا يُحفظ على القرص.")
        user_key = st.text_input("مفتاح Anthropic API (اختياري إن كان مضبوطاً على الخادم)", type="password",
                                 autocomplete="off", max_chars=220)
        if st.button("✍️ اكتب التقرير", type="primary"):
            try:
                with st.spinner("جاري كتابة التقرير..."):
                    self._store.report = self._c.reports.generate(r, user_key, client_id(), COUNTRIES[r.request.country].sales_seasons)
            except SmartBuyerError as e:
                st.html(Components.error(e.user_message))
            except Exception:                                   # noqa: BLE001
                log.exception("report failed")
                st.html(Components.error(SmartBuyerError.user_message))
        if self._store.report:
            st.markdown(self._store.report)                     # مُعقَّم مسبقاً، وبدون unsafe_allow_html
            st.download_button("⬇️ تحميل التقرير (Markdown)", self._store.report, "report.md", "text/markdown")

    def _reviews(self, r: ResearchResult) -> None:
        if not r.reviews:
            st.info("لم نجد مراجعات كافية لهذا المنتج.")
            return
        st.html("".join(Components.quote(t, lexicon_polarity(t)) for t in r.reviews[:12]))

    def _alternatives(self, r: ResearchResult) -> None:
        if not r.alternatives:
            st.info("لا توجد بدائل ظاهرة الآن.")
            return
        for a in r.alternatives[:8]:
            st.html(Components.alternative(a.title, a.body[:260]))
            if UrlPolicy.is_safe(a.url):
                st.link_button("المصدر", a.url)

    def _history(self, r: ResearchResult) -> None:
        h = self._c.research.history(r.request.product, r.request.country)
        if h["ts"].nunique() < 2:
            st.info("التاريخ لسه غير كافٍ. ابحث عن نفس المنتج على فترات (يومياً مثلاً) وسيظهر الرسم هنا.")
        else:
            st.plotly_chart(ChartFactory.history_line(h, r.currency), width="stretch", config={"displayModeBar": False})


class SmartBuyerApp:
    def __init__(self, c: Container):
        self._c, self._store = c, SessionStore()

    def run(self) -> None:
        ThemeManager.inject()
        if not self._passes_gate():
            return
        form = SidebarView(self._c).render()
        if form:
            self._search(form)
        result = self._store.result
        if result is None:
            st.html(Components.hero(self._stores()) + Components.steps() + Components.footer())
            return
        st.html(Components.hero((), compact=True))
        ResultsView(self._c, self._store).render(result)

    @staticmethod
    def _stores() -> list[str]:
        return sorted({s for p in COUNTRIES.values() for s in p.stores})

    def _passes_gate(self) -> bool:
        gate = self._c.gate
        if not gate.enabled or self._store.authed:
            return True
        st.html(Components.hero((), compact=True))
        with st.form("gate"):
            code = st.text_input("كود الوصول", type="password", autocomplete="off", max_chars=256)
            if st.form_submit_button("دخول", type="primary"):
                try:
                    gate.attempt(client_id(), code)
                    self._store.authed = True
                    st.rerun()
                except SmartBuyerError as e:
                    st.html(Components.error(e.user_message))
        return False

    def _search(self, f: SearchForm) -> None:
        holder = st.empty()
        try:
            v = self._c.validator
            req = ResearchRequest(v.product(f.product), v.country(f.country), v.extra(f.extra), v.budget(f.budget), v.weight(f.weight))
            with holder.container():
                st.html(Components.skeleton())
            self._store.result = self._c.research.research(req, client_id())
            self._store.report = None
        except SmartBuyerError as e:
            st.html(Components.error(e.user_message))
        except Exception:                                       # noqa: BLE001 — لا نعرض تفاصيل تقنية
            log.exception("unexpected error")
            st.html(Components.error(SmartBuyerError.user_message))
        finally:
            holder.empty()
