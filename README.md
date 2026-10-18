# SilkCocoon AI 🐛
### Automated Sericulture Cocoon Quality Inspection, Transparent Market Grading & Lot Valuation

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.38+-FF4B4B.svg)](https://streamlit.io/)
[![AI: Sarvam AI Vision](https://img.shields.io/badge/AI-Sarvam%20AI%20(gemma4)-FF6B35.svg)](https://dashboard.sarvam.ai)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## 1. Project Overview

**SilkCocoon AI** is an open, beginner-maintainable, multimodal AI application built for the sericulture (silk farming) industry. It enables smallholder silkworm farmers and silk reeling buyers to quickly inspect silkworm cocoons, detect commercial defects (such as uzifly parasite pierced holes, melting, or double cocoons), compute an objective sericulture quality grade, estimate an indicative market value in rupees, and grade an entire lot in one pass.

Unlike systems that fabricate scores or rely on opaque black-box models, **SilkCocoon AI** implements **transparent scoring logic**, provides **verifiable visual evidence**, and features a **safe manual-review state** whenever visual evidence is inadequate or ambiguous.

The multimodal vision provider is **Sarvam AI**, called through its OpenAI-compatible Chat Completion V2 endpoint. The image-capable model is **`gemma4`** (Gemma 4 31B, text + image input).

---

## 2. Problem Statement

In traditional silk-producing regions (e.g., Karnataka, Andhra Pradesh, Tamil Nadu in India, as well as parts of China, Brazil, and Vietnam):

1. **Subjective Manual Inspection:** Cocoon markets (mandis) rely on visual estimates by human intermediaries. Farmers frequently suffer arbitrary price cuts due to disputed defect rates.
2. **Hidden Pierced & Melted Defects:** Parasitic uzifly larvae bore exit holes in cocoons. A single pierced cocoon breaks the continuous 800–1,500-meter silk filament, making automated reeling impossible.
3. **Lack of Digital Transparency:** Smallholder farmers lack access to laboratory testing tools before traveling to distant auction markets.

---

## 3. Key Features

- **Multi-Source Image Input:** Drag-and-drop file upload (`.jpg`, `.png`, `.webp`) and live camera capture from mobile devices or laptops.
- **Strict In-Memory Validation:** Validates image format, prevents file-size overflows, and processes photos in RAM without permanent disk writes.
- **Multimodal AI Analysis (Sarvam AI):** Evaluates shape uniformity, shell compactness, surface cleanliness, and colour type using a verified Vision-Language model.
- **Auditable Sericulture Scoring:** Transparent scoring based on Central Silk Board and FAO commercial grading benchmarks.
- **Severe Defect Safeguards:** Automatically caps fatal defects (uzifly pierced emergence or melted pupa) at **Reject** status.
- **Anti-Fabrication Guardrail (Manual Review):** Refuses to guess or generate random numbers if an image is blurry, poorly lit, or does not contain cocoons.
- **🧺 Batch Lot Grading (NEW):** Upload many cocoon photos at once. Each photo is graded independently, then rolled up into one lot report with grade distribution, weighted average score, defect frequency, and a lot recommendation. Export as CSV or JSON.
- **💰 Market Price Estimator (NEW):** Converts a grade into an indicative ₹/kg rate and lot value, with a colour/race multiplier, an optional moisture discount, and a user rate override for the local mandi price.
- **One-Click Test Gallery:** Four schematic test patterns pre-loaded for exercising image validation and the manual-review guardrail offline. They are simple drawings, not photographs, so a real model correctly routes them to **Manual Review** — upload a real photo for an actual grade.
- **Certificate Export:** Download an inspection audit report in standard JSON format.

---

## 4. Architecture

```text
[ Farmer / Buyer ]
       │
       ▼ (Mobile / Laptop Web UI)
┌──────────────────────────────────────────────────────────────┐
│                 Streamlit Dashboard (app.py)                 │
│  - Cocoon Inspector  - Batch Lot Grading  - Price Estimator  │
│  - Responsive UI / Camera Capture / Preset Gallery           │
└───────────┬────────────────────────────────────┬─────────────┘
            │ In-Memory Bytes                    │
            ▼                                    ▼
┌───────────────────────────┐   ┌──────────────────────────────┐
│ image_analysis.py         │   │ scoring.py                   │
│ - PIL Validation          │   │ - Domain Penalties           │
│ - Sarvam Vision Prompt    │──▶│ - Weighted Grading Math      │
│ - Inline base64 image     │   │ - Manual Review Guard        │
│ - JSON Response Validator │   └────────────┬─────────────────┘
└───────────┬───────────────┘                │
            │                                ▼
            ▼ (HTTPS REST)         ┌──────────────────────────────┐
┌───────────────────────────┐      │ batch.py  (lot rollup)       │
│ Sarvam AI Vision          │      │ market.py (₹ price estimate) │
│ Chat Completion V2        │      └──────────────────────────────┘
│ model: gemma4             │
└───────────────────────────┘
```

---

## 5. Model Information, License & Source

| Attribute | Specification |
| :--- | :--- |
| **Provider** | Sarvam AI (`https://api.sarvam.ai`) |
| **Endpoint** | `POST /v2/chat/completions` (OpenAI-compatible) |
| **Model Name** | `gemma4` — Gemma 4 31B (text + image input) |
| **Auth Header** | `api-subscription-key: <SARVAM_API_KEY>` |
| **Role in App** | Extracts visual features (shell compactness, surface cleanliness, shape symmetry) and identifies defect classes from the uploaded photo. |
| **Text-only Sarvam models** | `sarvam-105b`, `sarvam-105b-conversations`, `glm5.3`, `deepseekv4.1-flash` — these **cannot** read a photo and are auto-avoided by the app. |
| **Alternative / fallback** | The module also supports any image-capable model you enable, and self-hosted overrides via `SARVAM_CHAT_URL`. |

> **Important:** the image-capable model is served on Sarvam's Chat Completion **V2 (beta)** route, which must be enabled for your API key. If `gemma4` is not listed for your key, request beta access from Sarvam.

---

## 6. Installation & Local Setup (Windows)

### Prerequisites
- Python 3.10 to 3.13 installed ([python.org](https://www.python.org/downloads/))
- Git installed ([git-scm.com](https://git-scm.com/))
- A Sarvam AI API key ([dashboard.sarvam.ai](https://dashboard.sarvam.ai))

### Step 1: Open PowerShell
```powershell
cd "c:\path\to\SilkCocoonAI"
```

### Step 2: Create and Activate a Virtual Environment
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```
*(If PowerShell displays an execution policy error, run: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`)*

### Step 3: Install Dependencies
```powershell
pip install -r requirements.txt
```

### Step 4: Configure API Credentials
Create a `.env` file from `.env.example`:
```powershell
Copy-Item .env.example .env
```
Open `.env` in Notepad and insert your real Sarvam API key:
```env
SARVAM_API_KEY=your_real_sarvam_key_here
SARVAM_MODEL=gemma4
MAX_UPLOAD_SIZE_MB=10
```

---

## 7. How to Run Locally

Start the Streamlit application:
```powershell
streamlit run app.py
```
The browser will automatically open at:
```text
http://localhost:8501
```

---

## 8. Running the Test Suite

SilkCocoon AI includes a thorough test suite verifying image safety, response parsing, the Sarvam provider wiring, market pricing, batch aggregation, and scoring logic. Provider tests mock the network, so they run offline.

```powershell
pytest -v
```

Test modules:
- `tests/test_image_validation.py` — image format, size, and resolution guardrails.
- `tests/test_scoring.py` — grading math, fatal-defect rejection, and manual-review guards.
- `tests/test_ai_parsing_and_errors.py` — JSON cleaning/parsing and missing-credential handling.
- `tests/test_sarvam_provider.py` — request shape, inline base64 image, auth/rate-limit error mapping.
- `tests/test_market.py` — price estimator rates, overrides, moisture discount, and lot totals.
- `tests/test_batch.py` — batch counts, weighted average, defect frequency, and CSV export.

---

## 9. Security & Privacy Safeguards

1. **Zero Secret Leaks:** API credentials are read exclusively from environment variables or masked session inputs. Secrets are barred from client responses and `.gitignore` prevents `.env` commits.
2. **RAM-Only Processing:** Uploaded photos are held in Python `BytesIO` streams during analysis and discarded after inference. No photos are written to disk.
3. **Upload Boundary Limits:** Files larger than 10MB or resolutions smaller than 64x64 are rejected before invoking AI models.
4. **Data Transmission Notice:** The interface explicitly informs users that images are transmitted over secure HTTPS to the inference endpoint.

---

## 10. Market Price Disclaimer

The rates in `market.py` are **indicative benchmark values** compiled for demonstration and hackathon purposes only. Real cocoon prices in Indian mandis move daily with the season, moisture content, race (bivoltine vs multivoltine/crossbreed), and local demand. Always confirm against the day's official Sericulture Department / market rate before making a commercial decision. This tool is not a substitute for a licensed buyer or the local cocoon market price bulletin.

---

## 11. Known Limitations

- **Shell Thickness / Floss Density:** A 2D photograph evaluates visible surface texture and firmness; it cannot weigh individual cocoons or calculate precise shell ratio without a physical balance scale.
- **Inner Melted Pupa Stains:** While exterior urine and disease stains are readily detected, mild internal pupal melting without shell penetration requires candling (light illumination).
- **Network Dependency:** Cloud inference requires an active internet connection.
- **Schematic Demo Samples:** The bundled gallery images are simple drawn test patterns, not photographs, so the vision model correctly declines to grade them. Real grading requires a real cocoon photograph.
- **Beta Vision Route:** The image-capable Sarvam model (`gemma4`) is served on the Chat Completion V2 (beta) route, enabled per API key. Verified working with a valid key.

---

## 12. Deployment Guide

### Deploy to Streamlit Community Cloud (Recommended & Free)
1. Push your repository to GitHub (ensure `.env` is NOT committed).
2. Go to [share.streamlit.io](https://share.streamlit.io/).
3. Connect your GitHub repository:
   - **Repository:** `your-username/SilkCocoonAI`
   - **Branch:** `main`
   - **Main file path:** `app.py`
4. Click **Advanced Settings** -> **Secrets**, and add your API key:
   ```toml
   SARVAM_API_KEY = "your_actual_key"
   SARVAM_MODEL = "gemma4"
   ```
5. Click **Deploy**. Your app is live with HTTPS!

---

## 13. Future Improvements Roadmap

- [x] **Batch Lot Grading:** Grade many cocoon photos at once with an aggregate lot report.
- [x] **Market Value Estimation:** Indicative ₹/kg rate and lot value by grade.
- [ ] **On-Device Edge Inference:** Integrate TensorFlow Lite or ONNX vision models for offline rural mandi operation.
- [ ] **Physical Scale Integration:** Connect Bluetooth balance scales to automatically compute Shell Ratio percentage.
- [ ] **Vernacular Voice Advisory:** Add audio explanations in Kannada, Telugu, Tamil, and Hindi using Sarvam's speech models.
- [ ] **Market Auction Direct Bidding:** Connect verified grades directly to local mandi trading boards.
