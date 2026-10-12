"""حساب درجة «القيمة مقابل السعر»."""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True, slots=True)
class ScoringWeights:
    rating: float = 0.45
    trust: float = 0.30
    sentiment: float = 0.25

    def __post_init__(self):
        if abs(self.rating + self.trust + self.sentiment - 1.0) > 1e-9:
            raise ValueError("Quality weights must sum to 1")


class ValueScorer:
    DEFAULT_RATING = 3.8

    def __init__(self, weights: ScoringWeights = ScoringWeights()):
        self._w = weights

    def score(self, offers: pd.DataFrame, sentiment: float, price_weight: float) -> pd.DataFrame:
        """value = w*price_score + (1-w)*quality ؛ كلها بين 0 و 1."""
        if offers.empty:
            return offers
        df = offers.copy()
        avg = df["rating"].mean() if df["rating"].notna().any() else self.DEFAULT_RATING
        rating = df["rating"].fillna(avg)
        median = df["price"].median()
        df["price_score"] = df["price"].min() / df["price"]
        df["quality_score"] = (self._w.rating * rating / 5 + self._w.trust * df["trust"] + self._w.sentiment * sentiment).clip(0, 1)
        df["value_score"] = (price_weight * df["price_score"] + (1 - price_weight) * df["quality_score"]).round(3)
        df["vs_median_pct"] = ((median - df["price"]) / median * 100).round(1)
        return df.sort_values(["value_score", "price"], ascending=[False, True]).reset_index(drop=True)
