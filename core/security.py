"""طبقة الأمان: تعقيم المدخلات والمخرجات، سياسة الروابط، تحديد المعدل، سلامة النماذج، الأسرار.

المبادئ:
  1. لا نثق بأي نص قادم من المستخدم أو من الويب أو من النموذج اللغوي (Untrusted by default).
  2. المدخلات تُتحقَّق (allow-list)، والمخرجات تُعقَّم (escape) حسب مكان العرض.
  3. لا أسرار في الـ logs أو الـ session، ولا رسائل أخطاء تقنية للمستخدم.
"""
from __future__ import annotations

import hashlib
import hmac
import html
import ipaddress
import json
import os
import re
import threading
import time
from collections import OrderedDict, deque
from pathlib import Path
from typing import Callable, Iterable
from urllib.parse import urlparse

import pandas as pd

from .config import COUNTRIES, Settings
from .errors import AuthError, IntegrityError, ValidationError

# محارف التحكم + محارف اتجاه النص الخفية (تُستخدم في الخداع البصري Bidi spoofing)
_CTRL = re.compile(r"[\x00-\x1f\x7f-\x9f\u200b-\u200f\u202a-\u202e\u2060-\u2069\ufeff]")
_TAG = re.compile(r"<[^<>]*>|<(?=[A-Za-z/!?])[^<>]*$")
_SPACES = re.compile(r"\s+")
_SEARCH_OPERATORS = re.compile(r"\b(?:site|inurl|intitle|intext|filetype|ext|cache|related|link):\S*", re.I)
_ALLOWED_QUERY = re.compile(r"^[\w\s\-+.,&/()'#\"]+$")


# ---------------------------------------------------------------- تعقيم النصوص
class TextSanitizer:
    """تنظيف النصوص حسب سياق العرض."""

    @staticmethod
    def clean(text: object, max_len: int = 500) -> str:
        """نص خام ← نص عادي آمن (بدون HTML أو محارف تحكم) بحد أقصى للطول."""
        s = html.unescape(str(text or ""))
        s = _TAG.sub(" ", s)
        s = _CTRL.sub(" ", s)
        s = _SPACES.sub(" ", s).strip()
        return s[:max_len]

    @staticmethod
    def escape(text: object) -> str:
        """للعرض داخل HTML — يمنع XSS."""
        return html.escape(str(text if text is not None else ""), quote=True)

    _IMG = re.compile(r"!\[[^\]]*\]\([^)]*\)")
    _REFDEF = re.compile(r"^\s*\[[^\]]+\]:\s*\S+.*$", re.M)
    _LINK = re.compile(r"\[([^\]]*)\]\(\s*([^)\s]*)[^)]*\)")
    _BARE = re.compile(r"https?://[^\s)\]>]+", re.I)

    @classmethod
    def markdown(cls, md: str, allowed_urls: Iterable[str] = ()) -> str:
        """تعقيم مخرجات النموذج اللغوي قبل عرضها كـ Markdown.

        - حذف HTML الخام والصور (قناة تسريب بيانات عبر Prompt Injection).
        - السماح فقط بالروابط الموجودة في قائمة بيضاء (روابط جئنا بها نحن).
        """
        allowed = set(allowed_urls)
        md = _CTRL.sub(" ", md or "")
        md = cls._IMG.sub("", md)
        md = cls._REFDEF.sub("", md)
        md = _TAG.sub("", md)
        md = cls._LINK.sub(lambda m: m.group(0) if m.group(2) in allowed else m.group(1), md)
        md = cls._BARE.sub(lambda m: m.group(0) if m.group(0) in allowed else "[رابط محجوب]", md)
        return md[:20_000]


# ---------------------------------------------------------------- سياسة الروابط
class UrlPolicy:
    _SCHEMES = {"http", "https"}

    @classmethod
    def is_safe(cls, url: object) -> bool:
        """يمنع javascript:/data: وبيانات الدخول داخل الرابط والعناوين المحلية/الخاصة."""
        if not isinstance(url, str) or not url or len(url) > 2048:
            return False
        if _CTRL.search(url) or any(c.isspace() for c in url):
            return False
        try:
            p = urlparse(url)
            host = (p.hostname or "").lower()
        except ValueError:
            return False
        if p.scheme.lower() not in cls._SCHEMES or not host or p.username or p.password:
            return False
        if host == "localhost" or host.endswith((".local", ".internal", ".localhost")):
            return False
        try:
            ip = ipaddress.ip_address(host)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
                return False
        except ValueError:
            pass  # اسم نطاق عادي
        return True


# ---------------------------------------------------------------- التحقق من المدخلات
class InputValidator:
    def __init__(self, settings: Settings):
        self._s = settings

    def product(self, raw: object) -> str:
        if not isinstance(raw, str):
            raise ValidationError("اكتب اسم المنتج.")
        if len(raw) > self._s.max_product_len * 3:      # قبل أي معالجة (حماية من النصوص الضخمة)
            raise ValidationError("اسم المنتج طويل جداً.")
        s = TextSanitizer.clean(raw, 10_000)
        s = _SEARCH_OPERATORS.sub(" ", s)
        s = _SPACES.sub(" ", s).strip()
        if len(s) < 2:
            raise ValidationError("اكتب اسم المنتج (حرفان على الأقل).")
        if len(s) > self._s.max_product_len:
            raise ValidationError(f"اسم المنتج يتجاوز {self._s.max_product_len} حرفاً.")
        if not _ALLOWED_QUERY.match(s):
            raise ValidationError("اسم المنتج يحتوي رموزاً غير مسموحة. استخدم حروفاً وأرقاماً فقط.")
        return s

    def extra(self, raw: object) -> str:
        if not raw:
            return ""
        s = _SPACES.sub(" ", _SEARCH_OPERATORS.sub(" ", TextSanitizer.clean(raw, 1_000))).strip()
        if len(s) > self._s.max_extra_len or (s and not _ALLOWED_QUERY.match(s)):
            raise ValidationError("الكلمات الإضافية غير صالحة.")
        return s

    def budget(self, raw: object) -> float:
        try:
            v = float(raw or 0)
        except (TypeError, ValueError):
            raise ValidationError("الميزانية يجب أن تكون رقماً.")
        if not (0 <= v <= self._s.max_budget) or v != v:   # v != v يكشف NaN
            raise ValidationError("الميزانية خارج النطاق المسموح.")
        return v

    @staticmethod
    def country(name: object) -> str:
        if name not in COUNTRIES:
            raise ValidationError("دولة غير مدعومة.")
        return str(name)

    @staticmethod
    def weight(raw: object) -> float:
        try:
            v = float(raw)
        except (TypeError, ValueError):
            raise ValidationError("قيمة الأولوية غير صالحة.")
        if not (0.0 <= v <= 1.0):
            raise ValidationError("قيمة الأولوية يجب أن تكون بين 0 و 1.")
        return v


# ---------------------------------------------------------------- تحديد المعدل
class SlidingWindowRateLimiter:
    """نافذة منزلقة آمنة للتعدد الخيطي. acquire() ترجع 0 إن سُمح، أو عدد الثواني للانتظار."""

    _MAX_KEYS = 10_000

    def __init__(self, max_calls: int, period_s: float, clock: Callable[[], float] = time.monotonic):
        self._max, self._period, self._clock = max_calls, period_s, clock
        self._hits: "OrderedDict[str, deque[float]]" = OrderedDict()
        self._lock = threading.Lock()

    def acquire(self, key: str) -> float:
        now = self._clock()
        with self._lock:
            q = self._hits.setdefault(key, deque())
            while q and now - q[0] >= self._period:
                q.popleft()
            if len(q) >= self._max:
                return max(0.0, self._period - (now - q[0]))
            q.append(now)
            self._hits.move_to_end(key)
            while len(self._hits) > self._MAX_KEYS:       # منع تضخم الذاكرة (DoS)
                self._hits.popitem(last=False)
            return 0.0

    def reset(self, key: str) -> None:
        with self._lock:
            self._hits.pop(key, None)


# ---------------------------------------------------------------- ملفات CSV
def csv_safe(df: pd.DataFrame) -> pd.DataFrame:
    """منع CSV/Formula Injection عند فتح الملف في Excel."""
    def fix(v):
        return "'" + v if isinstance(v, str) and v[:1] in ("=", "+", "-", "@", "\t", "\r") else v

    out = df.copy()
    for c in out.columns:
        if out[c].dtype == object or pd.api.types.is_string_dtype(out[c]):
            out[c] = out[c].map(fix)
    return out


# ---------------------------------------------------------------- سلامة النماذج
class ModelIntegrity:
    """ملفات joblib/pickle قد تنفّذ كوداً عند تحميلها؛ لذلك لا نحمّل إلا ملفاً مطابقاً للبصمة المسجلة وقت التدريب.

    ضع SMARTBUYER_MODEL_KEY (سر على السيرفر فقط) لتصبح البصمة HMAC لا يستطيع المهاجم تزويرها بتعديل manifest.json.
    """

    MANIFEST = "manifest.json"

    def __init__(self, model_dir: str | Path):
        self._dir = Path(model_dir)
        self._key = os.environ.get("SMARTBUYER_MODEL_KEY", "").encode() or None

    def _digest(self, path: Path) -> str:
        h = hmac.new(self._key, digestmod=hashlib.sha256) if self._key else hashlib.sha256()
        files = [path] if path.is_file() else sorted(p for p in path.rglob("*") if p.is_file())
        for f in files:
            h.update(f.name.encode() if path.is_file() else str(f.relative_to(path)).encode())
            with f.open("rb") as fh:
                for chunk in iter(lambda: fh.read(1 << 20), b""):
                    h.update(chunk)
        return h.hexdigest()

    def _load_manifest(self) -> dict:
        try:
            return json.loads((self._dir / self.MANIFEST).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def register(self, path: str | Path) -> None:
        p = Path(path)
        m = self._load_manifest()
        m[p.name] = self._digest(p)
        self._dir.mkdir(parents=True, exist_ok=True)
        (self._dir / self.MANIFEST).write_text(json.dumps(m, indent=2), encoding="utf-8")

    def verify(self, path: str | Path) -> bool:
        p = Path(path)
        expected = self._load_manifest().get(p.name)
        if not expected or not p.exists():
            return False
        return hmac.compare_digest(expected, self._digest(p))

    def require(self, path: str | Path) -> None:
        if not self.verify(path):
            raise IntegrityError()


# ---------------------------------------------------------------- الأسرار وبوابة الدخول
class SecretProvider:
    _KEY = re.compile(r"^sk-[A-Za-z0-9_\-]{20,200}$")

    @classmethod
    def anthropic_key(cls, server_key: str | None, user_key: str | None) -> str | None:
        """مفتاح السيرفر (env/secrets) له الأولوية؛ وإلا مفتاح المستخدم بعد التحقق من الصيغة. لا يُخزَّن في أي مكان."""
        key = (server_key or "").strip() or (user_key or "").strip()
        if not key:
            return None
        if not cls._KEY.match(key):
            raise ValidationError("صيغة مفتاح API غير صحيحة.")
        return key


class AccessGate:
    """بوابة دخول اختيارية بكود وصول، مقارنة ثابتة الزمن + قفل بعد محاولات فاشلة."""

    def __init__(self, settings: Settings, limiter: SlidingWindowRateLimiter):
        self._code = settings.access_code.encode()
        self._limiter = limiter

    @property
    def enabled(self) -> bool:
        return bool(self._code)

    def attempt(self, client_id: str, candidate: str) -> None:
        wait = self._limiter.acquire(client_id)
        if wait:
            raise AuthError(f"محاولات كثيرة. انتظر {int(wait) + 1} ثانية.")
        if not hmac.compare_digest(self._code, (candidate or "")[:256].encode()):
            raise AuthError()
        self._limiter.reset(client_id)
