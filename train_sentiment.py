"""تدريب نموذج تحليل مشاعر المراجعات (OOP).

  python train_sentiment.py --data reviews.csv --mode tfidf     # سريع، CPU
  python train_sentiment.py --data reviews.csv --mode bert      # أدق، يفضّل GPU (Colab)

الملف: CSV بعمودين text,label حيث label ∈ {positive, neutral, negative}
بعد التدريب تُسجَّل بصمة الملف في models/manifest.json — والتطبيق يرفض أي نموذج لا تطابق بصمته.
(للحماية الأقوى اضبط SMARTBUYER_MODEL_KEY قبل التدريب وعلى الخادم بنفس القيمة.)
"""
from __future__ import annotations

import argparse
from abc import ABC, abstractmethod
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split

from core.security import ModelIntegrity
from core.sentiment import BERT_DIR, TFIDF_FILE, normalize_ar

LABELS = ["negative", "neutral", "positive"]


class DatasetLoader:
    def __init__(self, path: str):
        self._path = path

    def load(self) -> pd.DataFrame:
        df = pd.read_csv(self._path).dropna(subset=["text", "label"])
        df["label"] = df["label"].astype(str).str.lower().str.strip()
        df = df[df["label"].isin(LABELS)].drop_duplicates("text")
        df["text"] = df["text"].astype(str).map(normalize_ar)
        print(df["label"].value_counts())
        return df

    @staticmethod
    def split(df: pd.DataFrame):
        return train_test_split(df, test_size=0.15, stratify=df["label"], random_state=42)


class Trainer(ABC):
    def __init__(self, model_dir: str):
        self._dir = Path(model_dir)
        self._integrity = ModelIntegrity(self._dir)

    @abstractmethod
    def train(self, df: pd.DataFrame) -> None: ...


class TfidfTrainer(Trainer):
    def train(self, df: pd.DataFrame) -> None:
        import joblib
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.linear_model import LogisticRegression
        from sklearn.metrics import classification_report
        from sklearn.pipeline import Pipeline

        tr, te = DatasetLoader.split(df)
        pipe = Pipeline([
            ("tfidf", TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), min_df=2, sublinear_tf=True, max_features=300_000)),
            ("clf", LogisticRegression(max_iter=2000, C=4, class_weight="balanced")),
        ])
        pipe.fit(tr["text"], tr["label"])
        print(classification_report(te["label"], pipe.predict(te["text"]), digits=3))
        self._dir.mkdir(parents=True, exist_ok=True)
        out = self._dir / TFIDF_FILE
        joblib.dump(pipe, out)
        self._integrity.register(out)
        print("saved + registered ->", out)


class BertTrainer(Trainer):
    def __init__(self, model_dir: str, base: str, epochs: int = 3, lr: float = 2e-5, batch: int = 16):
        super().__init__(model_dir)
        self._base, self._epochs, self._lr, self._bs = base, epochs, lr, batch

    def train(self, df: pd.DataFrame) -> None:
        import numpy as np
        import torch
        from datasets import Dataset
        from sklearn.metrics import f1_score
        from transformers import (AutoModelForSequenceClassification, AutoTokenizer, DataCollatorWithPadding,
                                  Trainer as HFTrainer, TrainingArguments)

        l2i = {l: i for i, l in enumerate(LABELS)}
        df = df.assign(label=df["label"].map(l2i))
        tr, te = DatasetLoader.split(df)
        tok = AutoTokenizer.from_pretrained(self._base)
        enc = lambda b: tok(b["text"], truncation=True, max_length=128)          # noqa: E731
        dtr = Dataset.from_pandas(tr[["text", "label"]], preserve_index=False).map(enc, batched=True)
        dte = Dataset.from_pandas(te[["text", "label"]], preserve_index=False).map(enc, batched=True)
        model = AutoModelForSequenceClassification.from_pretrained(
            self._base, num_labels=3, id2label=dict(enumerate(LABELS)), label2id=l2i)

        def metrics(p):
            preds = np.argmax(p.predictions, axis=1)
            return {"macro_f1": f1_score(p.label_ids, preds, average="macro"), "acc": float((preds == p.label_ids).mean())}

        args = TrainingArguments(
            output_dir="runs", num_train_epochs=self._epochs, learning_rate=self._lr,
            per_device_train_batch_size=self._bs, per_device_eval_batch_size=self._bs * 2, weight_decay=0.01,
            warmup_ratio=0.1, eval_strategy="epoch", save_strategy="epoch", load_best_model_at_end=True,
            metric_for_best_model="macro_f1", fp16=torch.cuda.is_available(), report_to="none")
        trainer = HFTrainer(model=model, args=args, train_dataset=dtr, eval_dataset=dte, processing_class=tok,
                            data_collator=DataCollatorWithPadding(tok), compute_metrics=metrics)
        trainer.train()
        print(trainer.evaluate())
        out = self._dir / BERT_DIR
        trainer.save_model(str(out), safe_serialization=True)                     # safetensors
        tok.save_pretrained(out)
        self._integrity.register(out)
        print("saved + registered ->", out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--mode", choices=["tfidf", "bert"], default="tfidf")
    ap.add_argument("--base", default="aubmindlab/bert-base-arabertv02")
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--model-dir", default="models")
    a = ap.parse_args()
    df = DatasetLoader(a.data).load()
    (TfidfTrainer(a.model_dir) if a.mode == "tfidf" else BertTrainer(a.model_dir, a.base, a.epochs)).train(df)


if __name__ == "__main__":
    main()
