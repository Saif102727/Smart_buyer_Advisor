"""تحليل مشاعر المراجعات — Strategy Pattern: Lexicon / TF-IDF / BERT، مع اختيار تلقائي وتحقق من سلامة الملفات."""
from __future__ import annotations

import re
import threading
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Sequence

from .logs import get_logger
from .security import ModelIntegrity

log = get_logger("sentiment")

TFIDF_FILE = "sentiment_tfidf.joblib"
BERT_DIR = "sentiment_bert"


def normalize_ar(text: str) -> str:
    """توحيد النص العربي — نفس الدالة تُستخدم في التدريب والتنبؤ."""
    text = re.sub(r"[\u064B-\u0652\u0640]", "", text or "")
    text = re.sub("[إأآا]", "ا", text).replace("ى", "ي").replace("ة", "ه")
    text = re.sub(r"http\S+|www\.\S+", " ", text)
    text = re.sub(r"(.)\1{2,}", r"\1\1", text)
    return re.sub(r"\s+", " ", text).strip().lower()


_POS = ["ممتاز", "رائع", "جميل", "انصح", "سريع", "خرافي", "يستاهل", "جامد", "تحفه", "هايل", "فخم", "عظمه",
        "great", "excellent", "love", "best", "fast", "recommend", "worth", "perfect"]
_NEG = ["سيء", "سيئ", "مشكله", "مشاكل", "عيب", "عيوب", "بطيء", "ضعيف", "تعطل", "زباله", "وحش", "فاشل", "نصب",
        "مضروب", "تقليد", "bad", "poor", "problem", "issue", "slow", "broken", "worst", "fake", "scam"]
_NEG_PHRASES = re.compile(r"(?:لا|ما|مش|مو)\s+(?:انصح|يستاهل)|not recommend|don'?t buy")
POS_WORDS = tuple(normalize_ar(w) for w in _POS)
NEG_WORDS = tuple(normalize_ar(w) for w in _NEG)


def lexicon_counts(text: str) -> tuple[int, int]:
    t = normalize_ar(text)
    neg = len(_NEG_PHRASES.findall(t))
    t = _NEG_PHRASES.sub(" ", t)
    return sum(w in t for w in POS_WORDS), neg + sum(w in t for w in NEG_WORDS)


def lexicon_polarity(text: str) -> int:
    p, n = lexicon_counts(text)
    return (p > n) - (p < n)


class SentimentAnalyzer(ABC):
    name = "base"

    @abstractmethod
    def score(self, texts: Sequence[str]) -> float:
        """متوسط الإيجابية بين 0 و1."""

    @staticmethod
    def pros_cons(texts: Sequence[str]) -> tuple[int, int]:
        pc = [lexicon_counts(t) for t in texts]
        return sum(p for p, _ in pc), sum(n for _, n in pc)


class LexiconAnalyzer(SentimentAnalyzer):
    name = "lexicon"

    def score(self, texts: Sequence[str]) -> float:
        if not texts:
            return 0.6
        vals = []
        for t in texts:
            p, n = lexicon_counts(t)
            vals.append(0.5 if p == n else 0.5 + 0.5 * (p - n) / (p + n))
        return sum(vals) / len(vals)


class TfidfAnalyzer(SentimentAnalyzer):
    name = "tfidf"

    def __init__(self, path: Path):
        import joblib
        self._model = joblib.load(path)       # آمن فقط لأن Factory تحقق من البصمة قبل الوصول هنا

    def score(self, texts: Sequence[str]) -> float:
        if not texts:
            return 0.6
        proba = self._model.predict_proba([normalize_ar(t) for t in texts])
        return float(proba[:, list(self._model.classes_).index("positive")].mean())


class BertAnalyzer(SentimentAnalyzer):
    name = "bert"
    _POS, _NEG_ = {"positive", "label_2", "pos"}, {"negative", "label_0", "neg"}

    def __init__(self, path: Path):
        from transformers import pipeline
        self._lock = threading.Lock()
        self._pipe = pipeline("text-classification", model=str(path), tokenizer=str(path), truncation=True,
                              max_length=128, model_kwargs={"use_safetensors": True})   # safetensors فقط (بدون pickle)

    def score(self, texts: Sequence[str]) -> float:
        if not texts:
            return 0.6
        with self._lock:
            out = self._pipe([normalize_ar(t)[:500] for t in texts])
        vals = [o["score"] if o["label"].lower() in self._POS else
                1 - o["score"] if o["label"].lower() in self._NEG_ else 0.5 for o in out]
        return sum(vals) / len(vals)


class SentimentFactory:
    """يختار أفضل محلل متاح: BERT ← TF-IDF ← Lexicon، ولا يحمّل أي نموذج لم تتطابق بصمته."""

    def __init__(self, model_dir: str):
        self._dir = Path(model_dir)
        self._integrity = ModelIntegrity(self._dir)

    def create(self) -> SentimentAnalyzer:
        bert = self._dir / BERT_DIR
        if bert.is_dir() and self._integrity.verify(bert):
            try:
                return BertAnalyzer(bert)
            except Exception as exc:          # noqa: BLE001
                log.warning("BERT unavailable: %s", type(exc).__name__)
        elif bert.is_dir():
            log.warning("BERT model rejected: integrity check failed")
        tfidf = self._dir / TFIDF_FILE
        if tfidf.is_file() and self._integrity.verify(tfidf):
            try:
                return TfidfAnalyzer(tfidf)
            except Exception as exc:          # noqa: BLE001
                log.warning("TF-IDF unavailable: %s", type(exc).__name__)
        elif tfidf.is_file():
            log.warning("TF-IDF model rejected: integrity check failed")
        return LexiconAnalyzer()
