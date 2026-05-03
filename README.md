# 📡 DART Disclosure Alert Bot

An automated bot that monitors [DART](https://dart.fss.or.kr/) (Korea's Electronic Disclosure System) filings, generates AI-powered summaries with risk assessments, and delivers alerts via Telegram.

Built for **recurring contract pattern tracking** and **investment research candidate discovery** — not short-term trading signals.

---

## 🎯 Key Features

**Automated Disclosure Collection** — Fetches recent filings from the OpenDART API and filters by target keywords including supply contracts, facility investments, and asset acquisitions.

**Duplicate Alert Prevention** — Maintains a SQLite database of processed filings to eliminate redundant notifications.

**AI-Powered Summary + Risk Assessment** — Leverages Claude API to generate concise summaries and automatically evaluate 6 risk indicators per filing.

**Real-Time Telegram Alerts** — Delivers formatted alert messages to a designated Telegram chat whenever a relevant filing is detected.

**Recurring Contract Tracking** — Cross-references historical filings for the same entity to identify repeat contract patterns.

---

## ⚠️ Risk Assessment Framework

Every alert includes the following 6-point risk check:

1. Undisclosed counterparty
2. Excessively long contract duration (3+ years flagged)
3. Repeated correction filings
4. Contract value disproportionate to recent revenue
5. Recent abnormal stock price movement
6. Outsized contract by a loss-making entity

> Items that cannot be determined from available data are marked as "Requires original document review."

---

## 🏗️ Project Structure

```
dart-alert-bot/
├── dart_alert_bot.py    # Main bot script
├── db_setup.py          # Database schema & helper functions
├── test_telegram.py     # Telegram connection test
├── test_dart.py         # DART API connection test
├── test_claude.py       # Claude API summary test
├── run_bot.sh           # Shell script for scheduled execution
├── requirements.txt     # Python dependencies
├── .env                 # API keys (excluded from version control)
├── .gitignore           # Git ignore rules
├── seen_disclosures.db  # Filing history database (excluded from version control)
└── bot_log.txt          # Execution log (excluded from version control)
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
  Generate summary via Claude API
  + 6-point risk assessment
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

| Column | Type | V1 | V2+ | Description |
|--------|------|:--:|:---:|-------------|
| `rcept_no` | TEXT (PK) | ✅ | ✅ | Filing receipt number |
| `corp_name` | TEXT | ✅ | ✅ | Company name |
| `stock_code` | TEXT | ✅ | ✅ | Stock ticker code |
| `report_nm` | TEXT | ✅ | ✅ | Filing title |
| `rcept_dt` | TEXT | ✅ | ✅ | Filing date |
| `dart_url` | TEXT | ✅ | ✅ | Link to original filing |
| `contract_name` | TEXT | — | ✅ | Contract name |
| `contract_amount` | INTEGER | — | ✅ | Contract value |
| `recent_revenue` | INTEGER | — | ✅ | Recent revenue |
| `contract_to_revenue_ratio` | REAL | — | ✅ | Contract-to-revenue ratio |
| `counterparty` | TEXT | — | ✅ | Counterparty |
| `contract_start_date` | TEXT | — | ✅ | Contract start date |
| `contract_end_date` | TEXT | — | ✅ | Contract end date |
| `is_correction` | INTEGER | ✅ | ✅ | Correction filing flag |
| `raw_text` | TEXT | — | ✅ | Raw filing text |
| `summary` | TEXT | ✅ | ✅ | AI-generated summary |
| `matched_keyword` | TEXT | ✅ | ✅ | Matched filter keyword |

> V2 will auto-populate contract detail columns by crawling and parsing original DART filing documents.

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
python test_telegram.py    # 1. Verify Telegram connection
python test_dart.py        # 2. Verify DART API connection
python test_claude.py      # 3. Verify Claude API connection
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
- [ ] V1.1: Daily scheduled execution via cron
- [ ] V2: DART original document crawling and contract detail parsing
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

> ⚖️ This project does not constitute investment advice or securities recommendations. The accuracy of disclosure information should be verified against original DART filings. AI-generated summaries are provided for informational purposes only.├── .gitignore           # Git ignore rules
├── seen_disclosures.db  # Filing history DB (not tracked by Git)
└── bot_log.txt          # Execution log (not tracked by Git)
```

---

## 🔄 How It Works

```
[Runs daily at 16:00 KST on weekdays]
        │
        ▼
  Fetch filings from OpenDART API
        │
        ▼
  Filter by 7 keywords
        │
        ▼
  Check SQLite for duplicates
  (Already seen → Skip)
        │
        ▼
  Summarize with Claude API + Risk check
        │
        ▼
  Send Telegram alert
        │
        ▼
  Save to DB (for recurring contract tracking)
```

---

## 🗄️ Database Schema

Designed for recurring contract tracking with room for future expansion.

| Column | Type | V1 | V2 Planned | Description |
|--------|------|:--:|:----------:|-------------|
| `rcept_no` | TEXT (PK) | ✅ | ✅ | Filing receipt number |
| `corp_name` | TEXT | ✅ | ✅ | Company name |
| `stock_code` | TEXT | ✅ | ✅ | Stock ticker code |
| `report_nm` | TEXT | ✅ | ✅ | Filing title |
| `rcept_dt` | TEXT | ✅ | ✅ | Filing date |
| `dart_url` | TEXT | ✅ | ✅ | Link to original filing |
| `contract_name` | TEXT | - | ✅ | Contract name |
| `contract_amount` | INTEGER | - | ✅ | Contract value |
| `recent_revenue` | INTEGER | - | ✅ | Recent revenue |
| `contract_to_revenue_ratio` | REAL | - | ✅ | Contract-to-revenue ratio |
| `counterparty` | TEXT | - | ✅ | Counterparty |
| `contract_start_date` | TEXT | - | ✅ | Contract start date |
| `contract_end_date` | TEXT | - | ✅ | Contract end date |
| `is_correction` | INTEGER | ✅ | ✅ | Whether it's a correction filing |
| `raw_text` | TEXT | - | ✅ | Raw filing text |
| `summary` | TEXT | ✅ | ✅ | AI-generated summary |
| `matched_keyword` | TEXT | ✅ | ✅ | Matched keyword |

> In V2, contract details will be auto-parsed by crawling the original DART filing documents.

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
git clone https://github.com/your-username/dart-alert-bot.git
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

### Step-by-Step Testing

```bash
python test_telegram.py    # 1. Verify Telegram connection
python test_dart.py        # 2. Verify DART API connection
python test_claude.py      # 3. Verify Claude API connection
```

### Run

```bash
python dart_alert_bot.py
```

### Schedule (Weekdays at 16:00 KST)

```bash
crontab -e
# Add the following line:
0 16 * * 1-5 /path/to/dart-alert-bot/run_bot.sh
```

---

## 🛡️ Principles

- **No buy/sell recommendations.** Claude acts solely as a "disclosure summary intern."
- **Every alert includes a risk check.** Items that can't be assessed are marked accordingly.
- **Investment decisions are the user's responsibility.** This bot is an information organizing tool, not financial advice.

---

## 🗺️ Roadmap

- [x] V1: Filing collection → AI summary → Telegram alert
- [ ] V2: DART original document crawling, auto-parse contract details
- [ ] V3: Recurring contract pattern analysis, counterparty network tracking
- [ ] V4: Stock price data integration, auto-calculate contract-to-revenue ratio

---

## 🛠️ Tech Stack

- **Language:** Python 3
- **AI:** Claude API (Anthropic)
- **Data:** OpenDART API
- **Notifications:** Telegram Bot API
- **Database:** SQLite
- **Scheduling:** crontab

---

## 📜 License

This project was built for personal learning and portfolio purposes.

> ⚖️ This project is not intended as investment advice or stock recommendations. The accuracy of disclosure information is based on DART original filings. AI summaries are for reference only.
