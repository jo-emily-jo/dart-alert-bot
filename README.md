# 📡 DART Disclosure Alert Bot

An automated bot that monitors DART (Korea's Electronic Disclosure System) filings, summarizes them with AI, and sends alerts via Telegram.

Designed not for short-term trading, but for **tracking recurring contract patterns** and **discovering investment research candidates**.

---

## 🎯 Key Features

**Automated Disclosure Collection** — Fetches recent filings from the OpenDART API and filters them by keywords such as supply contracts, facility investments, and asset acquisitions.

**Duplicate Alert Prevention** — Stores processed filings in a SQLite database to ensure no disclosure is alerted twice.

**AI Summary + Risk Check** — Uses Claude API to generate concise summaries and automatically flags 6 risk indicators for each filing.

**Telegram Notifications** — Sends formatted alert messages to your Telegram chat whenever a relevant filing is detected.

**Recurring Contract Tracking** — Queries past filings for the same company from the database to detect repeat contract patterns.

---

## ⚠️ Risk Check Items

Every alert includes the following 6 risk checks:

1. Undisclosed counterparty
2. Excessively long contract period (3+ years)
3. Repeated correction filings
4. Contract amount disproportionate to recent revenue
5. Recent sharp stock price increase
6. Large contract by a loss-making company

> Items that cannot be determined are marked as "Requires original document review."

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
├── .env                 # API keys (not tracked by Git)
├── .gitignore           # Git ignore rules
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
