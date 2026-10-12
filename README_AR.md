# Smart Buyer — دليل التشغيل والتدريب والأفكار

## 1) التشغيل
```bash
python -m venv venv && source venv/bin/activate      # ويندوز: venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
python -m pytest -q tests                             # 17 اختباراً (وحدات + تكامل + واجهة)
```
**الأسرار** (لا تضعها في الكود): أنشئ `.streamlit/secrets.toml` أو متغيرات بيئة:
```toml
ANTHROPIC_API_KEY = "sk-ant-..."     # اختياري: لو ضُبط على الخادم لا يحتاج المستخدم إدخال مفتاح
```
```bash
export SMARTBUYER_ACCESS_CODE="كود-سري"     # بوابة دخول اختيارية (مهمة لو التطبيق عام)
export SMARTBUYER_MODEL_KEY="سر-طويل-عشوائي" # HMAC لبصمات النماذج (نفس القيمة وقت التدريب والتشغيل)
docker build -t smart-buyer . && docker run -p 8501:8501 smart-buyer
```

## 2) البنية (OOP + فصل الطبقات)
```
app.py                  نقطة الدخول (3 أسطر)
core/                   منطق العمل — بدون Streamlit (قابل للاختبار)
  config.py             Settings + CountryProfile (غير قابلة للتعديل)
  security.py           TextSanitizer • UrlPolicy • InputValidator • RateLimiter • ModelIntegrity • AccessGate
  search.py             SearchProvider (ABC) ← DuckDuckGoProvider (استبدله بـ SerpAPI/Keepa بسهولة)
  parsing.py            PriceParser • RatingParser
  scoring.py            ValueScorer
  sentiment.py          SentimentAnalyzer (Strategy): Lexicon / TF-IDF / BERT + SentimentFactory
  report.py             ReportService (Claude) مع حماية Prompt Injection
  service.py            ResearchService (Facade) + TTLCache
  storage.py            PriceRepository (SQLite)
  container.py          Composition Root (حقن الاعتماديات)
ui/                     theme.py (CSS/حركة) • components.py (HTML آمن) • charts.py • app.py (Views)
train_sentiment.py      TfidfTrainer / BertTrainer
tests/                  pytest
```
**معادلة القيمة:** `value = w × (أقل_سعر / السعر) + (1-w) × (0.45×تقييم + 0.30×ثقة المتجر + 0.25×رضا المراجعات)`

## 2-ب) الأمان — ما الذي تمت حمايته؟
| التهديد | الحماية |
|---|---|
| **XSS** | كل نص ديناميكي يمر عبر `escape()`؛ العرض بـ `st.html` (DOMPurify)؛ لا `unsafe_allow_html` مع بيانات خارجية |
| **روابط خبيثة** (`javascript:` / `data:` / عناوين محلية) | `UrlPolicy` تسمح بـ http/https فقط وتمنع بيانات الدخول داخل الرابط والـ IP الخاص |
| **Prompt Injection** (نص مسموم في صفحة ويب) | البيانات داخل `<data>` + تعليمات نظام صارمة + تعقيم مخرجات النموذج: حذف الصور وHTML وكل رابط ليس من قائمتنا البيضاء (يمنع تسريب البيانات عبر روابط الصور) |
| **حقن في الاستعلامات** | استعلامات SQL مُعلَّمة فقط؛ إزالة مشغّلات البحث `site:` و`inurl:` من مدخلات المستخدم؛ allow-list للحروف |
| **Bidi / محارف خفية** | إزالة محارف التحكم واتجاه النص |
| **CSV/Formula Injection** | `csv_safe` تضيف `'` قبل `= + - @` |
| **تنفيذ كود عبر ملف النموذج** (pickle) | لا يُحمَّل نموذج إلا بعد مطابقة SHA-256/HMAC؛ BERT بصيغة safetensors فقط |
| **إساءة الاستخدام / DoS / استنزاف رصيد API** | حدود معدل لكل جلسة ولكل التطبيق (بحث + تقارير)، كاش 15 دقيقة، حدود طول المدخلات، سقف للذاكرة |
| **تسريب الأسرار** | المفتاح من الخادم أو الإدخال فقط، لا يُخزَّن ولا يُسجَّل (Redacting log filter)، ولا تُعرض رسائل أخطاء تقنية |
| **تخمين كود الدخول** | مقارنة ثابتة الزمن + قفل بعد 5 محاولات |
| **CSRF/CORS** | مفعّلة في `.streamlit/config.toml` |
| **حاوية Docker** | مستخدم غير root |

> ⚠️ **حدود صادقة:** لا يوجد "أمان 100%". إن نشرت التطبيق علناً فضع خلفه HTTPS (Nginx/Cloudflare)، وفعّل `SMARTBUYER_ACCESS_CODE`، وحدّث المكتبات دورياً (`pip-audit`).
> وتذكّر أن الأسعار تُستخرج من نتائج البحث العامة فقد تكون قديمة؛ للمشاريع التجارية استخدم APIs رسمية.

---

## 3) التدريب خطوة بخطوة (نموذج تحليل مشاعر المراجعات)

### الخطوة 1 — جمع البيانات
اختار واحد أو أكتر:
- **Hugging Face Datasets:** ابحث عن `arabic_100k_reviews`, `labr`, `hard`, `ar_res_reviews`, `ArSarcasm` (راجع الرخصة).
- **داتا خاصة بيك:** مراجعات منتجات من متاجر مصرية/خليجية (بشرط تسمح شروط الموقع)، أو من عملائك.
- **أهم نصيحة:** اللهجة المصرية والخليجية مختلفة عن الفصحى، فلازم 20–30% من البيانات بلهجة بلدك المستهدفة.

الحد الأدنى: **3,000** مراجعة (TF-IDF) — الأفضل **20,000+** للـ BERT، مع توازن تقريبي بين الأصناف.

### الخطوة 2 — التنسيق
ملف `reviews.csv`:
```
text,label
"المنتج ممتاز وسريع جدا",positive
"وصل مكسور والخدمة زفت",negative
"عادي مفيش حاجة مميزة",neutral
```

### الخطوة 3 — التنظيف (`normalize_ar` في core/sentiment.py)
- إزالة التشكيل والتطويل، توحيد (أ إ آ ← ا) و(ى ← ي) و(ة ← ه).
- إزالة الروابط، تقليل الحروف المكررة ("جمييييل" ← "جميل").
- **لا تحذف** الإيموجي لو بتفيد (👍 👎) — ممكن تحولها لكلمات.
- إزالة المكرر `drop_duplicates` عشان ما يحصلش تسريب بين train وtest.

### الخطوة 4 — المقسّم
85% تدريب / 15% اختبار (مع `stratify`). الأفضل تضيف مجموعة **validation** منفصلة وما تلمسش الـ test إلا في النهاية.

### الخطوة 5 — نموذج أساسي (Baseline)
```bash
python train_sentiment.py --data reviews.csv --mode tfidf
```
بياخد دقائق على CPU. سجّل الـ **macro-F1**؛ ده الرقم اللي لازم النموذج الأكبر يتفوق عليه.

### الخطوة 6 — Fine-tuning لـ BERT عربي
1. افتح **Google Colab** وفعّل GPU (Runtime → Change runtime type → T4).
2. ```bash
   pip install transformers datasets accelerate scikit-learn joblib pandas
   ```
3. ارفع مجلد المشروع (أو `reviews.csv` + مجلد `core` + `train_sentiment.py`) ثم:
   ```bash
   python train_sentiment.py --data reviews.csv --mode bert --epochs 3
   ```
4. نماذج مقترحة (`--base`):
   - `aubmindlab/bert-base-arabertv02` ← افتراضي، ممتاز للفصحى.
   - `CAMeL-Lab/bert-base-arabic-camelbert-da` ← أفضل مع اللهجات.
   - `UBC-NLP/MARBERTv2` ← الأفضل غالبًا للسوشيال ميديا واللهجة المصرية.

**Hyperparameters المبدئية:**
| المعامل | القيمة |
|---|---|
| learning rate | 2e-5 (جرّب 3e-5 / 5e-5) |
| batch size | 16 (قلّله لـ 8 لو الذاكرة خلصت) |
| epochs | 3 (زيادة فوق 4 غالبًا Overfitting) |
| max_length | 128 |
| warmup | 10% |
| weight decay | 0.01 |

### الخطوة 7 — التقييم
- راقب **macro-F1** وليس الـ accuracy فقط (خصوصًا لو الأصناف غير متوازنة).
- اطبع **confusion matrix** وراجع 50 خطأ يدويًا: لو أغلبها "neutral" اللي اتصنفت غلط، حسّن تعريف الصنف الأوسط أو ضيف أمثلة.
- لو training-F1 عالي وtest-F1 واطي = Overfitting ← زوّد البيانات / قلّل epochs / زوّد dropout.
- لو الاتنين واطيين = Underfitting ← نموذج أكبر / بيانات أنضف / epochs أكتر.

### الخطوة 8 — التحسين
- **Class weights** لو صنف نادر.
- **Data augmentation:** ترجمة عكسية (عربي→إنجليزي→عربي)، استبدال مرادفات.
- **Active learning:** خلّي التطبيق يسجّل التنبؤات اللي ثقتها < 0.6، راجعها يدويًا وضيفها لبيانات التدريب (دورة تحسين مستمرة).
- جرّب **LoRA/PEFT** لو الـ GPU ضعيف.

### الخطوة 9 — الدمج
بعد التدريب هيتحفظ النموذج في `models/` (`sentiment_bert/` أو `sentiment_tfidf.joblib`) مع بصمة في `manifest.json`. التطبيق **بيكتشفه تلقائيًا**
وهتشوف اسمه في الشريط الجانبي. (BERT له الأولوية على TF-IDF.)

### الخطوة 10 — المراقبة
احفظ عينة من التنبؤات شهريًا وراجعها؛ اللغة والمنتجات بتتغير (Data drift).

---

## 4) أفكار تنقل المشروع لمستوى احترافي

**ذكاء الشراء**
1. **كاشف المراجعات المزيفة:** مؤشرات (تكرار نص، مراجعات في نفس اليوم، لغة مبالغ فيها) + نموذج تصنيف.
2. **توقّع السعر "اشتري الآن/انتظر"** بنموذج سلاسل زمنية (Prophet/XGBoost) على تاريخ الأسعار + مواسم التخفيضات.
3. **التكلفة الكلية (TCO):** سعر + شحن + جمارك + ضمان + استهلاك كهرباء + قطع غيار على 3 سنين.
4. **مقارنة بين الدول** (سعر + شحن + جمارك + ضريبة) ← "اشتريه من الإمارات ولا مصر؟".
5. **كاشف الوكيل الرسمي vs الموازي** والتحقق من الضمان والـ IMEI/الرقم التسلسلي.
6. **سوق المستعمل** (OLX, Dubizzle, Opensooq) مع تقدير "سعر عادل" وتحذير من النصب.
7. **حاسبة التقسيط:** مقارنة فوائد البنوك/المتاجر وتحديد أرخص طريقة دفع وعروض البطاقات.

**تجربة المستخدم**
8. **تنبيهات الأسعار** على Telegram/WhatsApp/إيميل عند نزول السعر عن رقم معين (جدولة بـ APScheduler/GitHub Actions).
9. **مساعد محادثة** (`st.chat_input`) يسأل: "أنا مصمم، ميزانيتي 30 ألف، أنصحني بلابتوب" بدل نموذج بحث جامد.
10. **قراءة مواصفات من صورة/PDF** (رفع صورة منتج أو عرض سعر) باستخدام Vision.
11. **قائمة مفضلة + مقارنة جنب بعض** (حتى 3 منتجات) مع جدول مواصفات.
12. **تقرير PDF احترافي** بشعارك + مشاركة برابط.

**هندسة**
13. فصل الـ Backend بـ **FastAPI** + Redis للتخزين المؤقت + Celery للمهام الخلفية.
14. استخدام **APIs رسمية** بدل البحث العام (SerpAPI / Keepa / Affiliate APIs).
15. **RAG** على كتيبات المواصفات والمراجعات التقنية للأجوبة الدقيقة.
16. **Docker + CI/CD + اختبارات (pytest)** ونشر على Streamlit Cloud / Render / VPS.
17. **تسجيل دخول وحسابات** (Supabase/Firebase) + خطة اشتراك + عمولات Affiliate كنموذج دخل.
18. **تقييم جودة** دوري للنموذج مع لوحة مراقبة (Evidently / MLflow).
