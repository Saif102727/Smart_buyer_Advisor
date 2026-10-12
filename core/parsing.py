"""استخراج الأسعار والتقييمات من نصوص حرة (عربي/إنجليزي)."""
from __future__ import annotations

import re
from typing import Iterable

_AR_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩٬٫", "0123456789,.")
_NUM = r"\d{1,3}(?:[.,]\d{3})+(?:[.,]\d{1,2})?|\d+(?:[.,]\d{1,2})?"
# أسعار الأقساط الشهرية ليست سعر المنتج
_INSTALLMENT = re.compile(r"^\W{0,3}(?:شهري|قسط|تقسيط|/\s*mo|per\s*month|monthly|installment|x\s*\d)", re.I)


def _to_float(raw: str) -> float:
    s = raw
    if "," in s and "." in s:
        dec = "," if s.rfind(",") > s.rfind(".") else "."
        thou = "." if dec == "," else ","
        s = s.replace(thou, "").replace(dec, ".")
    elif "," in s or "." in s:
        sep = "," if "," in s else "."
        parts = s.split(sep)
        s = "".join(parts) if (len(parts) > 2 or len(parts[-1]) == 3) else ".".join(parts)
    return float(s)


class PriceParser:
    MIN_PRICE, MAX_PRICE = 1.0, 100_000_000.0

    def __init__(self, currency_words: Iterable[str]):
        alts = "|".join(re.escape(w) for w in sorted(currency_words, key=len, reverse=True))
        self._before = re.compile(rf"(?<!\w)(?:{alts})\s*({_NUM})(?!\d)", re.I)
        self._after = re.compile(rf"(?<![\d.,])({_NUM})\s*(?:{alts})(?!\w)", re.I)

    def prices(self, text: str) -> list[float]:
        text = (text or "").translate(_AR_DIGITS)
        found: list[tuple[int, float]] = []
        for rx in (self._before, self._after):
            for m in rx.finditer(text):
                if _INSTALLMENT.match(text[m.end(): m.end() + 24]):
                    continue
                try:
                    v = _to_float(m.group(1))
                except ValueError:
                    continue
                if self.MIN_PRICE <= v <= self.MAX_PRICE:
                    found.append((m.start(), v))
        return [v for _, v in sorted(found)]


class RatingParser:
    _RX = re.compile(r"(\d(?:[.,]\d)?)\s*(?:/|out of|من|stars?)\s*5\b", re.I)

    @classmethod
    def rating(cls, text: str) -> float | None:
        m = cls._RX.search((text or "").translate(_AR_DIGITS))
        if not m:
            return None
        try:
            v = float(m.group(1).replace(",", "."))
        except ValueError:
            return None
        return v if 0 < v <= 5 else None
