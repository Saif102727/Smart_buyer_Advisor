"""رسوم Plotly بنفس هوية التطبيق."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

PALETTE = ["#F5B335", "#35D39A", "#3AA7C9", "#EF476F", "#B197FC", "#FF8F3D", "#9DB4B5"]
SAND, LINE = "#F1E8D4", "rgba(241,232,212,.12)"


class ChartFactory:
    @staticmethod
    def _style(fig: go.Figure, height: int = 380) -> go.Figure:
        fig.update_layout(
            height=height, margin=dict(l=10, r=10, t=30, b=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="IBM Plex Sans Arabic, Segoe UI, sans-serif", color=SAND), colorway=PALETTE,
            legend=dict(bgcolor="rgba(0,0,0,0)", orientation="h", y=-0.2), hoverlabel=dict(bgcolor="#123036", font_size=13))
        fig.update_xaxes(gridcolor=LINE, zeroline=False)
        fig.update_yaxes(gridcolor=LINE, zeroline=False)
        return fig

    @classmethod
    def value_scatter(cls, df: pd.DataFrame, currency: str) -> go.Figure:
        fig = px.scatter(df, x="price", y="value_score", color="store", size=df["trust"].clip(lower=0.2) * 40,
                         hover_name="title", hover_data={"price": ":,.0f", "value_score": ":.2f", "store": False},
                         labels={"price": f"السعر ({currency})", "value_score": "درجة القيمة", "store": "المتجر"})
        fig.update_traces(marker=dict(line=dict(width=1, color=SAND), opacity=.9))
        return cls._style(fig)

    @classmethod
    def price_bars(cls, df: pd.DataFrame, currency: str) -> go.Figure:
        top = df.sort_values("price").head(10)
        fig = go.Figure(go.Bar(x=top["price"], y=top["store"], orientation="h", marker_color=PALETTE[0],
                               text=[f"{p:,.0f}" for p in top["price"]], textposition="outside"))
        fig.update_layout(xaxis_title=f"السعر ({currency})", yaxis=dict(autorange="reversed"))
        return cls._style(fig, 340)

    @classmethod
    def history_line(cls, hist: pd.DataFrame, currency: str) -> go.Figure:
        h = hist.copy()
        h["ts"] = pd.to_datetime(h["ts"])
        low = h.groupby("ts")["price"].min().reset_index()
        fig = px.line(low, x="ts", y="price", markers=True, labels={"ts": "التاريخ", "price": f"أقل سعر ({currency})"})
        fig.update_traces(line=dict(color=PALETTE[1], width=3), marker=dict(size=8))
        return cls._style(fig, 340)
