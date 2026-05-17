# 🤖 AI Tender Intelligence System

Automated government tender scraping, AI analysis, ranking, and dashboard — powered by **CrewAI**, **CPPP Portal**, and **OpenRouter**.

---

## 🚀 Quick Start

1. **Double-click `START_HERE.bat`** — interactive menu for everything

Or use individual commands in `c:\Users\ryash\Tenderai-project`:

```powershell
# 1. Fetch live tenders from CPPP
uv run python cppp_bulk_fetch.py "" 2

# 2. Launch dashboard
uv run streamlit run dashboard.py

# 3. Start auto-scheduler (every 6h)
uv run python scheduler.py
```

---

## 📁 Project Structure

```
Tenderai-project/
│
├── START_HERE.bat              ← Master launcher (start here!)
├── run_dashboard.bat           ← Launch Streamlit dashboard
├── run_cppp_fetch.bat          ← Fetch from CPPP portal
├── run_scheduler.bat           ← Start auto-scheduler
├── run_pipeline.bat            ← Run full CrewAI pipeline
│
├── dashboard.py                ← Streamlit UI (3-tab dashboard)
├── main.py                     ← CLI entrypoint
├── cppp_bulk_fetch.py          ← Fast standalone CPPP fetcher
├── scheduler.py                ← Background auto-scheduler
├── company_profile.json        ← Your company's profile
├── .env                        ← API keys
│
├── scraper/
│   └── cppp_scraper.py         ← Real CPPP scraper (requests + BS4)
│
├── src/
│   ├── crew.py                 ← CrewAI orchestrator
│   ├── agents.py               ← 7 AI agents
│   ├── tasks.py                ← Sequential tasks
│   └── tools/
│       ├── scraper_tool.py     ← CPPP scraper tool
│       ├── pdf_tool.py         ← PDF extraction tool
│       ├── db_tool.py          ← Database storage tool
│       └── notification_tool.py ← Smart alerts tool
│
├── database/
│   ├── db.py                   ← SQLite connection
│   ├── models.py               ← SQLAlchemy ORM models
│   └── save_tender.py          ← Legacy JSON saver
│
└── tenders.db                  ← SQLite database (auto-created)
```

---

## 🏗️ Architecture

```
CPPP Portal
    ↓  (requests + BeautifulSoup)
cppp_scraper.py
    ↓
cppp_bulk_fetch.py  ──────────────────────────┐
    ↓ (OpenRouter / GPT-3.5)                  │
AI Analysis (budget, risk, type, deadline)    │
    ↓                                         │
Company Profile Matching                      │
    ↓                                         │
Match Score (0-100)                           │
    ↓                                         │
SQLite Database  ←────────────────────────────┘
    ↓
Streamlit Dashboard (dashboard.py)
    ├── 📋 Tenders tab    (scored tender cards)
    ├── 📊 Analytics tab  (charts + CSV export)
    └── 🔔 Notifications  (alerts + scheduler log)
```

---

## 🤖 CrewAI Agents (Full Pipeline)

| # | Agent | Role |
|---|-------|------|
| 1 | **Scraper** | Navigates CPPP with Playwright |
| 2 | **PDF Processor** | Extracts text from tender PDFs |
| 3 | **AI Analyst** | Extracts budget, EMD, deadline, risk |
| 4 | **Matcher** | Compares against company profile |
| 5 | **Ranker** | Assigns match score 0–100 |
| 6 | **DB Manager** | Saves to SQLite |
| 7 | **Notifier** | Sends alerts for high-priority tenders |

---

## ⚙️ Configuration

### `.env`
```env
OPENROUTER_API_KEY=sk-or-v1-...
```

### `company_profile.json`
```json
{
  "name": "Your Company",
  "experience_years": 8,
  "specialization": ["Road Construction", "IT Infrastructure"],
  "max_emd_capacity": "10 Lakh"
}
```

### Scheduler (`scheduler.py`)
```python
SCHEDULE_INTERVAL_HOURS = 6   # How often to auto-fetch
PAGES_PER_RUN = 3             # Pages per keyword category
KEYWORD_CATEGORIES = [        # Keywords to watch
    "", "Road", "Construction", "Water", "IT", ...
]
```

---

## 🔧 Troubleshooting

| Issue | Fix |
|-------|-----|
| `ModuleNotFoundError: crewai` | Always use `uv run python ...` |
| `File does not exist: dashboard.py` | Run from `c:\Users\ryash\Tenderai-project` |
| Unicode / emoji errors | Batch files set `chcp 65001` and `PYTHONUTF8=1` automatically |
| Empty dashboard | Run `cppp_bulk_fetch.py` first to populate DB |
| Fetch errors from CPPP | Check internet connection; CPPP may throttle requests |
