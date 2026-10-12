"""مكوّنات HTML — كل نص ديناميكي يمر عبر TextSanitizer.escape (منع XSS)، ولا روابط خام داخل HTML."""
from __future__ import annotations

from typing import Sequence

import pandas as pd

from core.security import TextSanitizer

_e = TextSanitizer.escape


def _fmt(v: float) -> str:
    return f"{v:,.0f}"


class Components:
    # ------------------------------------------------------------ الواجهة
    @staticmethod
    def hero(stores: Sequence[str], compact: bool = False) -> str:
        if compact:
            return '<div class="hero compact"><h1>🛒 مستشار الشراء الذكي</h1></div>'
        chips = "".join(f'<span class="chip">{c}</span>' for c in
                        ("🔎 متاجر موثوقة", "⚖️ سعر × جودة", "💬 تحليل المراجعات", "📉 تاريخ الأسعار", "🛡️ تحذير من النصب"))
        items = "".join(f"<span>{_e(s)}</span>" for s in stores)
        return f"""
<div class="hero">
  <div>
    <h1>اشترِ بأقل سعر… وبأعلى جودة</h1>
    <p>اكتب اسم المنتج واختر دولتك. نجمع العروض من المتاجر، نقرأ المراجعات، ونحسب لك أفضل قيمة مقابل السعر بدل أرخص رقم فقط.</p>
    <div class="chips">{chips}</div>
  </div>
  <div class="tag-wrap" aria-hidden="true">
    <div class="swing"><div class="string"></div>
      <div class="tag"><b>قيمة أعلى</b><span>سعر أقل</span></div></div>
  </div>
</div>
<div class="ticker" aria-hidden="true"><div class="ticker-track">{items}{items}</div></div>"""

    @staticmethod
    def section(title: str, hint: str = "") -> str:
        small = f"<small>{_e(hint)}</small>" if hint else ""
        return f'<div class="sec">{_e(title)}{small}</div>'

    @staticmethod
    def steps() -> str:
        data = (("ابحث", "اكتب اسم المنتج واختر الدولة والميزانية."),
                ("قارن", "نعرض لك العروض مرتبة حسب القيمة، لا حسب السعر فقط."),
                ("قرّر", "تقرير واضح: اشترِ الآن أم انتظر، ومن أين."))
        body = "".join(f'<div class="step"><b><span class="n">{i}</span>{t}</b><span>{d}</span></div>'
                       for i, (t, d) in enumerate(data, 1))
        return f'<div class="steps">{body}</div>'

    @staticmethod
    def skeleton() -> str:
        return ('<div class="skel-grid">' + '<div class="skel s"></div>' * 3 + "</div>"
                '<div class="skel-grid">' + '<div class="skel"></div>' * 3 + "</div>")

    @staticmethod
    def footer() -> str:
        return ('<div class="foot">الأسعار مستخرجة من نتائج البحث العامة وقد تختلف عن السعر الحالي في المتجر. '
                "تأكد من السعر والضمان والبائع قبل الدفع، ولا تشارك بيانات بطاقتك خارج المتجر الرسمي.</div>")

    @staticmethod
    def error(message: str) -> str:
        return f'<div class="err" role="alert">⚠️ {_e(message)}</div>'

    # ------------------------------------------------------------ مؤشرات
    @classmethod
    def stats(cls, items: Sequence[tuple[str, str, str, str, str]]) -> str:
        """items: (label, value, unit, sub, accent_css_var)"""
        cards = "".join(
            f'<div class="stat" style="--i:{i};--accent:var(--{_e(acc)})"><div class="lbl">{_e(lbl)}</div>'
            f'<div class="val">{_e(val)}<small>{_e(unit)}</small></div><div class="sub">{_e(sub)}</div></div>'
            for i, (lbl, val, unit, sub, acc) in enumerate(items))
        return f'<div class="stats">{cards}</div>'

    @staticmethod
    def gauge(value: float, title: str, subtitle: str, color: str = "mint") -> str:
        p = max(0.0, min(1.0, float(value)))
        return (f'<div class="gauge"><div class="ring" style="--p:{p:.3f};--c:var(--{_e(color)})" role="img" aria-label="{_e(title)} {p*100:.0f}%">'
                '<svg viewBox="0 0 100 100"><circle class="track" cx="50" cy="50" r="42" fill="none" stroke-width="9"/>'
                '<circle class="bar" cx="50" cy="50" r="42" fill="none" stroke-width="9"/></svg>'
                f'<div class="num">{p*100:.0f}%</div></div>'
                f'<div class="txt"><b>{_e(title)}</b><span>{_e(subtitle)}</span></div></div>')

    @classmethod
    def gauges(cls, sentiment: float, best_value: float, insights: Sequence[str]) -> str:
        ins = "".join(f"<div>{_e(i)}</div>" for i in insights)
        return ('<div class="gauges">'
                + cls.gauge(sentiment, "رضا المشترين", "من تحليل المراجعات", "mint")
                + cls.gauge(best_value, "درجة أفضل عرض", "سعر × جودة × ثقة", "saffron")
                + f'<div class="insight">{ins}</div></div>')

    # ------------------------------------------------------------ تذكرة العرض
    @staticmethod
    def ticket(label: str, kind: str, row: pd.Series, currency: str) -> str:
        cls_ = {"best": "pulse", "cheap": "cheap", "safe": "safe"}.get(kind, "")
        rating = row.get("rating")
        stars = ""
        if pd.notna(rating):
            full = int(round(float(rating)))
            stars = f'<span class="stars" aria-label="تقييم {float(rating):.1f} من 5">{"★" * full}{"☆" * (5 - full)}</span>'
        score = max(0, min(100, float(row["value_score"]) * 100))
        return (f'<div class="ticket-wrap"><div class="ticket">'
                f'<div class="top"><span class="badge {cls_}">{_e(label)}</span>'
                f'<div class="store">{_e(row["store"])}</div><div class="ttl">{_e(row["title"])}</div></div>'
                f'<div class="bottom"><div class="price">{_fmt(float(row["price"]))}<small>{_e(currency)}</small></div>'
                f'<div class="meter" role="img" aria-label="درجة القيمة {score:.0f} من 100"><i style="--w:{score:.0f}"></i></div>'
                f'<div class="rate"><span>{stars}</span><span>ثقة المتجر {float(row["trust"])*100:.0f}%</span></div></div>'
                '</div></div>')

    # ------------------------------------------------------------ مراجعات وبدائل
    @staticmethod
    def quote(text: str, polarity: int) -> str:
        cls_ = "pos" if polarity > 0 else "neg" if polarity < 0 else ""
        return f'<div class="quote {cls_}">{_e(text)}</div>'

    @staticmethod
    def alternative(title: str, body: str) -> str:
        return f'<div class="alt"><b>{_e(title)}</b><p>{_e(body)}</p></div>'
