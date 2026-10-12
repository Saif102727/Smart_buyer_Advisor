# 🛒 Smart Buyer Advisor

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.30%2B-FF4B4B.svg)](https://streamlit.io/)
[![Pytest](https://img.shields.io/badge/Testing-Pytest-yellow.svg)](https://docs.pytest.org/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)

**Smart Buyer Advisor** is an AI-powered e-commerce research and decision-support agent. It aggregates product pricing across multiple search providers, cleans and structures live market data, analyzes Arabic user sentiment using custom NLP/Transformer models, and generates insightful buyer reports using Anthropic Claude.

---

## ⚡ Quick Start

### 1. Environment Setup
```bash
# Clone the repository
git clone https://github.com/Saif102727/Smart_buyer_Advisor.git
cd Smart_buyer_Advisor

# Create and activate a virtual environment
python -m venv venv
# On Linux/macOS:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration & Secrets
Create a `.streamlit/secrets.toml` file in the root directory (or set environment variables):
```toml
ANTHROPIC_API_KEY = "sk-ant-..." # Optional: If set on server, users won't need to provide their own API key
```

Optional access gate & security secrets:
```bash
export SMARTBUYER_ACCESS_CODE="your-secure-access-code"  # Optional entry passphrase
export SMARTBUYER_MODEL_KEY="your-hmac-secret-key"      # HMAC secret key for model integrity verification
```

### 3. Run the Application & Tests
```bash
# Run Streamlit UI
streamlit run app.py

# Run test suite (17 Unit + Integration + UI tests)
python -m pytest -q tests
```

### 4. Docker Deployment
```bash
docker build -t smart-buyer .
docker run -p 8501:8501 smart-buyer
```

---

## 🏗️ System Architecture & Design Patterns

The codebase adheres to **SOLID principles**, strict separation of concerns (Layered Architecture), and Object-Oriented Programming (OOP) without Streamlit dependencies in the core business layer.

```text
├── app.py                  # Minimal application entry point
├── core/                   # Pure business logic (Framework-agnostic & Testable)
│   ├── config.py           # Application Settings & Immutable Country Profiles
│   ├── security.py         # TextSanitizer, UrlPolicy, RateLimiter, AccessGate, ModelIntegrity
│   ├── search.py           # SearchProvider (ABC) → DuckDuckGoProvider (Extensible to SerpAPI/Keepa)
│   ├── parsing.py          # Robust Price & Rating Extractor
│   ├── scoring.py          # Multi-factor ValueScorer engine
│   ├── sentiment.py        # SentimentAnalyzer Strategy: Lexicon / TF-IDF / BERT + Factory
│   ├── report.py           # ReportService powered by Claude (Prompt-injection hardened)
│   ├── service.py          # ResearchService (Facade Pattern) + TTL Caching Layer
│   ├── storage.py          # SQLite Price History Repository
│   └── container.py        # Dependency Injection / Composition Root
├── ui/                     # Presentation Layer (Streamlit Views, CSS, Sanitized Components)
│   ├── theme.py            # Custom CSS & UI Animations
│   ├── components.py       # XSS-Safe HTML Rendering
│   ├── charts.py           # Plotly / Matplotlib Visualizations
│   └── app.py              # Main View controller
├── train_sentiment.py      # Sentiment Model Training CLI (TF-IDF & Arabic BERT Fine-Tuning)
└── tests/                  # Automated Pytest Suite
```

### 📐 Value Scoring Formula
The purchase value index is calculated as:
$$\text{Value} = w \cdot \left(\frac{\text{Min Price}}{\text{Item Price}}\right) + (1 - w) \cdot \left(0.45 \cdot \text{Rating} + 0.30 \cdot \text{Store Trust} + 0.25 \cdot \text{Sentiment Score}\right)$$

---

## 🛡️ Security Architecture & Threat Mitigation

| Threat Vector | Defense Mechanism |
|---|---|
| **XSS Vulnerabilities** | Dynamic text escaping via `html.escape()`; DOMPurify sanitization with `st.html`; No `unsafe_allow_html` on untrusted inputs. |
| **Malicious Links** | `UrlPolicy` enforces `http/https` protocols, blocks embedded credentials, and rejects local/private IP ranges. |
| **Prompt Injection** | Encapsulated inputs inside `<data>` tags with strict system constraints. Output sanitization strips images, raw HTML, and un-whitelisted URLs. |
| **SQL Injection** | Parameterized queries via SQLite driver; Query sanitization strips search operators (`site:`, `inurl:`). |
| **Unicode & Control Injection** | Bidi and hidden control character removal prior to execution. |
| **CSV / Formula Injection** | Safe CSV escaping by prefixing sensitive symbols (`=`, `+`, `-`, `@`) with `'`. |
| **Model Tampering (Pickle Code Execution)** | Model checksum validation via SHA-256 / HMAC prior to loading. BERT models restricted to `.safetensors` format. |
| **DoS / Resource Exhaustion** | Per-session and global Rate Limiters, 15-minute TTL caching, input length constraints, and memory caps. |
| **Credential Leakage** | Redacting log filters strip API keys from logs; raw exceptions are suppressed in end-user errors. |
| **Timing Attacks** | Constant-time string comparisons (`secrets.compare_digest`) on access code verification. |

---

## 🤖 NLP Sentiment Analysis & Training Pipeline

### Pipeline Overview
The repository includes a standalone CLI (`train_sentiment.py`) to fine-tune custom sentiment analysis models for Arabic e-commerce reviews (Modern Standard Arabic & Regional Dialects).

```
Raw Data ──> Normalization ──> Stratified Split ──> TF-IDF Baseline / BERT Fine-Tuning ──> HMAC Verification ──> Runtime Auto-Discovery
```

### Step-by-Step Training Guide

#### 1. Data Preparation
Format your dataset as a CSV file (`reviews.csv`) containing `text` and `label` columns:
```csv
text,label
"المنتج ممتاز وسريع جدا",positive
"وصل مكسور والخدمة سيئة",negative
"عادي لا يوجد شيء مميز",neutral
```

#### 2. Baseline Training (TF-IDF)
Train a fast CPU baseline model:
```bash
python train_sentiment.py --data reviews.csv --mode tfidf
```

#### 3. Deep Learning Fine-Tuning (Arabic BERT)
Run fine-tuning using PyTorch and Hugging Face Transformers (GPU recommended):
```bash
python train_sentiment.py --data reviews.csv --mode bert --epochs 3 --base aubmindlab/bert-base-arabertv02
```

**Recommended Base Models:**
* `aubmindlab/bert-base-arabertv02`: Best for Modern Standard Arabic (MSA).
* `CAMeL-Lab/bert-base-arabic-camelbert-da`: Best for dialectal Arabic reviews.
* `UBC-NLP/MARBERTv2`: Optimal for social media and local dialect nuances.

**Default Hyperparameters:**
* **Learning Rate:** `2e-5`
* **Batch Size:** `16`
* **Epochs:** `3`
* **Max Sequence Length:** `128`
* **Warmup Ratio:** `10%`
* **Weight Decay:** `0.01`

#### 4. Model Deployment & Auto-Discovery
Trained models are exported to `models/` (`sentiment_bert/` or `sentiment_tfidf.joblib`) with a cryptographic hash saved in `manifest.json`. The application auto-detects and loads the highest-priority valid model upon startup.

---

## 🛣️ Roadmap & Future Enhancements

- [ ] **Fake Review Detection:** NLP classifier to flag suspicious review bursts and repetitive phrasing.
- [ ] **Price Prediction ("Buy Now vs Wait"):** Time-series forecasting (Prophet/XGBoost) based on historical price trends and seasonal sales.
- [ ] **Total Cost of Ownership (TCO):** Calculate multi-year cost including shipping, import duties, warranties, and energy consumption.
- [ ] **Telegram / WhatsApp Price Alerts:** Background cron jobs notifying users when items drop below target thresholds.
- [ ] **Conversational Buyer Assistant:** Multi-turn AI advisor for personalized budget allocation and product comparison.
- [ ] **Vision Integration:** Extract product specifications directly from uploaded images or PDF quotation sheets.

---

## 📄 License

This project is licensed under the **GNU General Public License v3.0 (GPL-3.0)** - see the [LICENSE](LICENSE) file for full details. 

Copyright (C) 2026 Saif.