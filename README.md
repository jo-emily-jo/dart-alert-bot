# 📡 DART Disclosure Alert Bot

An automated bot that monitors [DART](https://dart.fss.or.kr/) (Korea's Electronic Disclosure System) filings, **crawls original filing documents**, generates AI-powered summaries with data-driven risk assessments, and delivers alerts via Telegram.

Built for **recurring contract pattern tracking** and **investment research candidate discovery** — not short-term trading signals.

---

## 🎯 Key Features

**Automated Disclosure Collection** — Fetches recent filings from the OpenDART API and filters by target keywords including supply contracts, facility investments, and asset acquisitions.

**Original Document Crawling** — Downloads and parses the full filing document from DART, extracting contract amounts, counterparties, contract periods, and revenue ratios directly from the source.

**AI-Powered Summary + Risk Assessment** — Feeds the actual filing content to Claude API, enabling data-driven summaries with concrete numbers instead of generic placeholders.

**Duplicate Alert Prevention** — Maintains a SQLite database of processed filings to eliminate redundant notifications.

**Real-Time Telegram Alerts** — Delivers formatted alert messages to a designated Telegram chat whenever a relevant filing is detected.

**Recurring Contract Tracking** — Cross-references historical filings for the same entity to identify repeat contract patterns.

---

## ⚠️ Risk Assessment Framework

Every alert includes a 6-point risk check, evaluated against actual filing data:

1. **Undisclosed counterparty** — Flags when the counterparty is redacted or generically described
2. **Excessively long contract duration** — Flags contracts exceeding 3 years with specific dates cited
3. **Repeated correction filings** — Flags corrections with the stated reason for revision
4. **Contract-to-revenue ratio** — Flags when contract value exceeds 30% of recent revenue, citing exact figures
5. **Recent abnormal stock price movement** — Flagged for separate verification
6. **Outsized contract by a loss-making entity** — Flagged for separate verification

### Before (V1) vs After (V1.5)

```
V1:  "Contract amount? Requires original document review"
V1:  "Counterparty?    Requires original document review"

V1.5: "Contract amount: ₩2.26B, 48.55% of recent revenue ⚠️"
V1.5: "Counterparty: Undisclosed (domestic manufacturer) ⚠️"
V1.5: "Contract period: 2026-03-25 ~ 2026-08-07 (4.4 months) ✅"
```

---

## 🏗️ Project Structure

```
dart-alert-bot/
├── dart_alert_bot.py      # Main bot script (V1.5: includes document crawling)
├── db_setup.py            # Database schema & helper functions
├── test_telegram.py       # Telegram connection test
├── test_dart.py           # DART API connection test
├── test_dart_detail.py    # DART original document crawling test
├── test_claude.py         # Claude API summary test
├── run_bot.sh             # Shell script for scheduled execution
├── requirements.txt       # Python dependencies
├── .env                   # API keys (excluded from version control)
├── .gitignore             # Git ignore rules
├── seen_disclosures.db    # Filing history database (excluded from version control)
└── bot_log.txt            # Execution log (excluded from version control)
```

---

## 🔄 System Architecture

```
[Scheduled daily at 16:00 KST, weekdays]
        │
        ▼
  Fetch filings via OpenDART API
        │
        ▼
  Keyword filtering (7 categories)
        │
        ▼
  Deduplicate against SQLite
  (Previously processed → Skip)
        │
        ▼
  Crawl original filing document     ← V1.5
  (Extract full text from DART XML)
        │
        ▼
  Generate summary via Claude API
  + 6-point risk assessment
  (with actual contract data)         ← V1.5
        │
        ▼
  Dispatch Telegram alert
        │
        ▼
  Persist to database
  (for recurring contract analysis)
```

---

## 🗄️ Database Schema

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

> V2 will auto-populate structured contract detail columns by parsing the crawled filing text.

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
ANTHROPIC_API_KEY=your_anthropic_api_key
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id
```

> **Note:** The codebase currently references `CLAUDE_API_KEY` internally. If you use `ANTHROPIC_API_KEY` in your `.env`, update the variable name in `dart_alert_bot.py` and `test_claude.py` accordingly — or vice versa. Ensure the key name is consistent across `.env` and all source files.

### Verification

```bash
python test_telegram.py      # 1. Verify Telegram connection
python test_dart.py          # 2. Verify DART API connection
python test_dart_detail.py   # 3. Verify DART document crawling
python test_claude.py        # 4. Verify Claude API connection
```

### Execution

```bash
python dart_alert_bot.py
```

### Scheduled Execution (Weekdays, 16:00 KST)

```bash
crontab -e
# Add the following line:
0 16 * * 1-5 /path/to/dart-alert-bot/run_bot.sh
```

---

## 🛡️ Disclaimer

- **This tool does not provide investment recommendations.** Claude operates solely as a "disclosure summary intern."
- **Every alert includes a structured risk assessment.** Items that cannot be evaluated are explicitly flagged.
- **All investment decisions are the sole responsibility of the user.** This bot is an information aggregation and summarization tool — not financial advice.

---

## 🗺️ Roadmap

- [x] V1: Filing collection → AI summary → Telegram alert
- [x] V1.5: Original document crawling → data-driven risk assessment
- [ ] V1.6: Daily scheduled execution via cron
- [ ] V2: Structured contract detail parsing and DB population
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

> ⚖️ This project does not constitute investment advice or securities recommendations. The accuracy of disclosure information should be verified against original DART filings. AI-generated summaries are provided for informational purposes only.
