# 📡 DART Toolkit — Disclosure Alert Bot + Korexis Lead Radar

Two independent tools built on a shared DART / Claude / Telegram / SQLite stack:

1. **Disclosure Alert Bot** (`dart_alert_bot.py`) — monitors [DART](https://dart.fss.or.kr/) (Korea's Electronic Disclosure System) filings, **crawls the original filing documents**, generates AI summaries with data-driven risk assessments, and sends Telegram alerts. Built for **recurring contract pattern tracking** and **investment research candidate discovery** — not short-term trading signals.

2. **Korexis Lead Radar** (`lead_radar.py`) — a **completely separate entry point** that scans DART disclosures to detect and rank Korean companies likely expanding into **Australia / Oceania** with potential **AASB S2 climate disclosure** exposure. This is a **B2B sales-fit evaluation, not an investment risk assessment.**

> The two tools share infrastructure (the same DART/Claude/Telegram call patterns and the same SQLite file, using separate tables) but never touch each other's code paths.

---

## 🎯 Disclosure Alert Bot

**Automated Disclosure Collection** — Fetches recent filings from the OpenDART API and filters by target keywords (supply contracts, facility investments, asset acquisitions).

**Original Document Crawling (V1.5)** — Downloads and parses the full filing document from DART, extracting contract amounts, counterparties, contract periods, and revenue ratios directly from the source text.

**AI-Powered Summary + Risk Assessment** — Feeds the actual filing content to the Claude API, enabling data-driven summaries with concrete numbers instead of generic placeholders.

**Duplicate Alert Prevention** — Maintains a SQLite database of processed filings to eliminate redundant notifications.

**Real-Time Telegram Alerts** — Delivers formatted alert messages to a designated Telegram chat whenever a relevant filing is detected.

### ⚠️ Risk Assessment Framework

Every alert includes a 6-point risk check, evaluated against actual filing data:

1. **Undisclosed counterparty** — Flags when the counterparty is redacted or generically described
2. **Excessively long contract duration** — Flags contracts exceeding 3 years, with specific dates cited
3. **Repeated correction filings** — Flags corrections with the stated reason for revision
4. **Contract-to-revenue ratio** — Flags when contract value exceeds 30% of recent revenue, citing exact figures
5. **Recent abnormal stock price movement** — Flagged for separate verification
6. **Outsized contract by a loss-making entity** — Flagged for separate verification

> Items that cannot be determined from available data are marked as "Requires original document review."

### Before (V1) vs After (V1.5)

```
V1:  "Contract amount? Requires original document review"
V1:  "Counterparty?    Requires original document review"

V1.5: "Contract amount: ₩2.26B, 48.55% of recent revenue ⚠️"
V1.5: "Counterparty: Undisclosed (domestic manufacturer) ⚠️"
V1.5: "Contract period: 2026-03-25 ~ 2026-08-07 (4.4 months) ✅"
```

### 🔄 How It Works

```
[Scheduled daily at 16:00 KST, weekdays]
        │
        ▼
  Fetch filings via OpenDART API
        │
        ▼
  Keyword filtering (supply contracts, investments, acquisitions)
        │
        ▼
  Deduplicate against SQLite (previously processed → skip)
        │
        ▼
  Crawl original filing document (extract full text from DART XML)   ← V1.5
        │
        ▼
  Generate summary via Claude API + 6-point risk assessment
  (with actual contract data)                                        ← V1.5
        │
        ▼
  Dispatch Telegram alert
        │
        ▼
  Persist to database (for recurring contract analysis)
```

---

## 🛰️ Korexis Lead Radar

Detects and ranks **sales leads** — Korean companies expanding into Australia/Oceania with likely AASB S2 climate-disclosure exposure — from public DART filings. **It does detection and ranking only; there is intentionally no automated outreach or emailing.** Only public corporate disclosure data is processed; no personal information is collected.

**Two-Stage Scoring**
- **Stage 1 — Local keyword scoring (gate):** A filing must contain a *primary* keyword (`호주`, `오세아니아`, `Australia`) or it is dropped. *Secondary* keywords add weighted points, with climate/ESG signals (`기후`, `탄소`, `온실가스`, `ESG`, `지속가능`) weighted highest as AASB S2 exposure signals. Low-fit industries (`건설`, `조선`, `방산`) are penalized.
- **Stage 2 — Claude fit scoring:** Surviving candidates are sent to Claude, which returns a structured JSON `fit_score` (0–100), estimated industry, Australia-relevance evidence, a recommended sales approach angle, and a hold reason.

**Operating Defaults**
- Source: **regular filings only** (`pblntf_ty=A` — annual/quarterly reports). A 90-day validation found major-event reports (type B) produced zero Australia leads, so B is excluded — the real leads live in the overseas-business / climate sections of regular report bodies.
- Lookback: **90 days**, deduped per company (`corp_code`), keeping each company's highest-scoring filing.
- Output: **`candidates.csv`** (sorted by `fit_score` descending, written row-by-row so partial runs are preserved) plus Telegram alerts for leads scoring ≥ 60.

### 🔄 How It Works

```
python lead_radar.py
        │
        ▼
  [1/3] Collect DART filings (type A, last 90 days, paginated)
        │
        ▼
  Skip already-scored filings (lead_candidates table)
        │
        ▼
  [2/3] Crawl full document text + local keyword scoring (gate)
        │
        ▼
  Dedup per company (keep highest candidate_score)
        │
        ▼
  [3/3] Claude fit scoring → JSON (fit_score, industry, angle, ...)
        │
        ▼
  Append to candidates.csv + save to lead_candidates + Telegram (fit ≥ 60)
```

> Alerts are labeled "sales lead detection — not an investment opinion" to keep the two tools' outputs clearly distinct.

---

## 🏗️ Project Structure

```
dart-alert-bot/
├── dart_alert_bot.py    # Disclosure alert bot (V1.5: includes document crawling)
├── lead_radar.py        # Korexis lead radar (separate entry point)
├── db_setup.py          # Database schema & helper functions
├── test_telegram.py     # Telegram connection test
├── test_dart.py         # DART API connection test
├── test_dart_detail.py  # DART original-document crawling test
├── test_claude.py       # Claude API summary test
├── run_bot.sh           # Shell script for scheduled execution
├── requirements.txt     # Python dependencies
├── .env                 # API keys (excluded from version control)
├── .gitignore           # Git ignore rules
├── seen_disclosures.db  # Filing/lead history database (excluded from version control)
├── candidates.csv       # Lead radar output (excluded from version control)
└── bot_log.txt          # Execution log (excluded from version control)
```

---

## 🗄️ Database Schema

Both tools use the same `seen_disclosures.db` file with **separate tables**.

### `disclosures` (Disclosure Alert Bot)

Designed for longitudinal contract tracking with forward-compatible expansion.

| Column | Type | V1 | V1.5 | V2+ | Description |
|--------|------|:--:|:----:|:---:|-------------|
| `rcept_no` | TEXT (PK) | ✅ | ✅ | ✅ | Filing receipt number |
| `corp_name` | TEXT | ✅ | ✅ | ✅ | Company name |
| `stock_code` | TEXT | ✅ | ✅ | ✅ | Stock ticker code |
| `report_nm` | TEXT | ✅ | ✅ | ✅ | Filing title |
| `rcept_dt` | TEXT | ✅ | ✅ | ✅ | Filing date |
| `dart_url` | TEXT | ✅ | ✅ | ✅ | Link to original filing |
| `contract_name` | TEXT | — | — | ✅ | Contract name |
| `contract_amount` | INTEGER | — | — | ✅ | Contract value |
| `recent_revenue` | INTEGER | — | — | ✅ | Recent revenue |
| `contract_to_revenue_ratio` | REAL | — | — | ✅ | Contract-to-revenue ratio |
| `counterparty` | TEXT | — | — | ✅ | Counterparty |
| `contract_start_date` | TEXT | — | — | ✅ | Contract start date |
| `contract_end_date` | TEXT | — | — | ✅ | Contract end date |
| `is_correction` | INTEGER | ✅ | ✅ | ✅ | Correction filing flag |
| `raw_text` | TEXT | — | ✅ | ✅ | Raw filing text |
| `summary` | TEXT | ✅ | ✅ | ✅ | AI-generated summary |
| `matched_keyword` | TEXT | ✅ | ✅ | ✅ | Matched filter keyword |

> V2 will auto-populate the structured contract-detail columns by parsing the crawled filing text.

### `lead_candidates` (Korexis Lead Radar)

| Column | Type | Description |
|--------|------|-------------|
| `rcept_no` | TEXT (PK) | Filing receipt number |
| `corp_code` | TEXT | DART corporate code |
| `corp_name` | TEXT | Company name |
| `report_nm` | TEXT | Filing title |
| `rcept_dt` | TEXT | Filing date |
| `matched_keywords` | TEXT | Keywords matched in Stage 1 |
| `candidate_score` | INTEGER | Local keyword score |
| `fit_score` | INTEGER | Claude sales-fit score (0–100) |
| `industry` | TEXT | Estimated industry |
| `australia_basis` | TEXT | Evidence of Australia relevance |
| `approach_angle` | TEXT | Recommended sales approach |
| `hold_reason` | TEXT | Reason to hold / needs review |
| `dart_url` | TEXT | Link to original filing |
| `scored_at` | TEXT | Timestamp (local time) |

---

## ⚙️ Setup & Usage

### Prerequisites

- Python 3.9+
- [OpenDART API Key](https://opendart.fss.or.kr/)
- [Anthropic API Key](https://console.anthropic.com/)
- [Telegram Bot Token](https://t.me/BotFather)
- Telegram Chat ID

### Installation

```bash
git clone https://github.com/jo-emily-jo/dart-alert-bot.git
cd dart-alert-bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Environment Variables

Create a `.env` file in the project root:

```env
DART_API_KEY=your_dart_api_key
CLAUDE_API_KEY=your_claude_api_key
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id
```

> Both `dart_alert_bot.py` and `lead_radar.py` read the Anthropic key from `CLAUDE_API_KEY` — keep that exact name consistent across `.env` and all source files.

### Verification

```bash
python test_telegram.py      # 1. Verify Telegram connection
python test_dart.py          # 2. Verify DART API connection
python test_dart_detail.py   # 3. Verify DART document crawling
python test_claude.py        # 4. Verify Claude API connection
```

### Execution

```bash
python dart_alert_bot.py    # Disclosure alert bot
python lead_radar.py        # Korexis lead radar → candidates.csv
```

### Scheduled Execution (Weekdays, 16:00 KST)

```bash
crontab -e
# Add the following line:
0 16 * * 1-5 /path/to/dart-alert-bot/run_bot.sh
```

---

## 🛡️ Disclaimer

- **This tool does not provide investment recommendations.** In the disclosure bot, Claude operates solely as a "disclosure summary intern."
- **The lead radar performs sales-fit detection only** — it does not produce investment opinions, and it collects no personal information (public corporate disclosures only).
- **Every disclosure alert includes a structured risk assessment.** Items that cannot be evaluated are explicitly flagged.
- **All investment decisions are the sole responsibility of the user.** This is an information aggregation and summarization tool — not financial advice.

---

## 🗺️ Roadmap

- [x] V1: Filing collection → AI summary → Telegram alert
- [x] V1.5: Original document crawling → data-driven risk assessment
- [x] Lead Radar: Australia / AASB S2 sales-lead detection and ranking (lead mode)
- [ ] V1.6: Daily scheduled execution via cron
- [ ] V2: Structured contract-detail parsing and DB population
- [ ] V3: Contract-to-revenue ratio calculation and recurring contract pattern analysis
- [ ] V4: Stock price and institutional flow integration

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3 |
| AI | Claude API (Anthropic) |
| Data Source | OpenDART API |
| Notifications | Telegram Bot API |
| Database | SQLite |
| Scheduling | crontab |

---

## 📜 License

This project was developed for personal learning and portfolio purposes.

> ⚖️ This project does not constitute investment advice or securities recommendations. The accuracy of disclosure information should be verified against original DART filings. AI-generated outputs are provided for informational purposes only.
