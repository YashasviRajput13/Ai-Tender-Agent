"""
Enhanced Tender Intelligence Dashboard
Automated dashboard with:
  - Live "Fetch Now" button (triggers real CPPP scrape)
  - Auto-refresh mode
  - Scheduler status monitor
  - Multi-tab layout (Dashboard / Analytics / Notifications log)
"""
import streamlit as st
import pandas as pd
import sys
import os
import subprocess
import time
from pathlib import Path
from datetime import datetime

# ── Path fix ──────────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.db import get_db, init_db
from database.models import Tender
from database.vector_db import get_vector_db

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = Path(PROJECT_DIR) / "scheduler.log"
NOTIF_FILE = Path(PROJECT_DIR) / "notifications.log"
FETCH_SCRIPT = Path(PROJECT_DIR) / "cppp_bulk_fetch.py"

# ── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Tender Intelligence System",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Dark Premium CSS ──────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, .stApp { font-family: 'Inter', sans-serif !important; }
.stApp { background: linear-gradient(135deg, #0a0a1a 0%, #0d0d25 100%); color: #e0e0f0; }
section[data-testid="stSidebar"] { background: #0e0e24 !important; border-right: 1px solid #1e1e4a; }
.stButton>button { background: linear-gradient(135deg, #7c3aed, #4f46e5) !important; color: white !important; border: none !important; border-radius: 8px !important; font-weight: 600 !important; padding: 0.5rem 1.2rem !important; transition: all 0.2s !important; }
.stButton>button:hover { transform: translateY(-1px); box-shadow: 0 4px 20px rgba(124,58,237,0.4) !important; }
div[data-testid="metric-container"] { background: linear-gradient(135deg, #12122e, #1a1a40) !important; border: 1px solid #2a2a5a !important; border-radius: 12px !important; padding: 16px !important; }
.stTabs [data-baseweb="tab-list"] { background: #0e0e24 !important; border-radius: 10px !important; }
.stTabs [data-baseweb="tab"] { color: #8888bb !important; font-weight: 500 !important; }
.stTabs [aria-selected="true"] { color: #a78bfa !important; background: #1e1e44 !important; border-radius: 8px !important; }
.tender-card { background: linear-gradient(135deg, #111128, #0f0f2e); border-radius: 14px; padding: 22px; margin-bottom: 16px; border-left: 5px solid #4CAF50; box-shadow: 0 4px 20px rgba(0,0,0,0.5); transition: transform 0.2s; }
.tender-card:hover { transform: translateY(-2px); box-shadow: 0 8px 30px rgba(0,0,0,0.6); }
.tender-card.high { border-left-color: #f44336; }
.tender-card.medium { border-left-color: #ff9800; }
.tender-card.low { border-left-color: #4CAF50; }
.score-pill { font-size: 1.1rem; font-weight: 700; padding: 5px 16px; border-radius: 30px; display: inline-block; }
.status-live { color: #4CAF50; font-weight: 600; animation: pulse 2s infinite; }
@keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.5; } }
.log-box { background: #080820; border: 1px solid #1a1a3a; border-radius: 8px; padding: 12px 16px; font-family: 'Courier New', monospace; font-size: 0.78rem; color: #88aaff; max-height: 300px; overflow-y: auto; white-space: pre-wrap; }
h1, h2, h3 { color: #c4b5fd !important; }
.stSelectbox label, .stMultiSelect label, .stSlider label, .stTextInput label { color: #8888bb !important; }
hr { border-color: #1e1e4a !important; }
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
col_title, col_status = st.columns([3, 1])
with col_title:
    st.title("🤖 AI Tender Intelligence System")
    st.markdown("*Real-time CPPP monitoring powered by CrewAI & OpenRouter*")
with col_status:
    now = datetime.now().strftime("%d %b %Y, %H:%M")
    st.markdown(f"<div style='text-align:right;padding-top:20px;color:#8888bb;font-size:0.85rem;'>🕐 {now}</div>", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Controls")

    # ── FETCH NOW ────────────────────────────────────────────────────────────
    st.markdown("### 🌐 Live Fetch")
    fetch_keyword = st.text_input("Keyword (optional)", placeholder="Road, IT, Water...")
    fetch_pages = st.selectbox("Pages to fetch", [1, 2, 3, 5], index=1)

    if st.button("🚀 Fetch Now from CPPP", use_container_width=True):
        with st.spinner(f"Scraping CPPP portal — {fetch_pages} page(s)..."):
            try:
                env = os.environ.copy()
                env["PYTHONUTF8"] = "1"          # force UTF-8 on Windows
                env["PYTHONIOENCODING"] = "utf-8"

                result = subprocess.run(
                    ["uv", "run", "python", str(FETCH_SCRIPT), fetch_keyword, str(fetch_pages)],
                    cwd=PROJECT_DIR,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=180,
                    env=env
                )
                if result.returncode == 0:
                    lines = [l for l in result.stdout.splitlines() if any(x in l for x in ["Saved", "Done", "Scraped", "[OK]", "[SAVED]", "WARN", "SKIP"])]
                    summary = "\n".join(lines[-6:]) if lines else "Fetch complete."
                    st.success(f"Done!\n{summary}")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error(f"Fetch had errors:\n{result.stderr[:400]}")
            except subprocess.TimeoutExpired:
                st.error("Fetch timed out after 3 minutes.")
            except Exception as e:
                st.error(f"Error: {e}")


    st.divider()

    # ── AUTO-REFRESH ─────────────────────────────────────────────────────────
    st.markdown("### 🔄 Auto-Refresh")
    auto_refresh = st.toggle("Enable Auto-Refresh", value=False)
    refresh_interval = st.selectbox("Interval", ["30s", "1 min", "5 min", "15 min"], index=1)
    if auto_refresh:
        interval_map = {"30s": 30, "1 min": 60, "5 min": 300, "15 min": 900}
        secs = interval_map[refresh_interval]
        st.markdown(f"<span class='status-live'>● Live — refreshing every {refresh_interval}</span>", unsafe_allow_html=True)
        time.sleep(secs)
        st.cache_data.clear()
        st.rerun()

    st.divider()

    # ── FILTERS ──────────────────────────────────────────────────────────────
    st.markdown("### 🔍 Filters")
    semantic_q = st.text_input("🧠 Semantic Search", placeholder="e.g. Road repair near river", help="Powered by RAG/Vector DB")
    search_q = st.text_input("🔎 Keyword Search", placeholder="Search exact keywords...")
    risk_opts = st.multiselect("⚠️ Risk Level", ["High", "Medium", "Low"], default=[])
    min_score = st.slider("🎯 Min Match Score", 0, 100, 0)
    sort_by = st.selectbox("📊 Sort By", ["Match Score ↓", "Match Score ↑", "Recommendation"])

    st.divider()
    st.markdown("### 📧 Email Alerts")
    st.markdown("<div style='font-size:0.8rem;color:#8888bb;'>Configure in `.env` file</div>", unsafe_allow_html=True)
    st.text_input("Alert Recipient", value=os.getenv("ALERT_RECIPIENT", "Not Configured"), disabled=True)

    st.divider()
    st.markdown("### 🤖 Scheduler")
    if LOG_FILE.exists():
        last_lines = LOG_FILE.read_text(encoding="utf-8").strip().split("\n")[-3:]
        for l in last_lines:
            st.markdown(f"<div style='font-size:0.75rem;color:#8888bb;'>{l}</div>", unsafe_allow_html=True)
    else:
        st.info("Run `run_scheduler.bat` to start auto-fetch every 6h.")

# ── Load Data ─────────────────────────────────────────────────────────────────
@st.cache_data(ttl=30)
def load_tenders():
    init_db()
    db = next(get_db())
    rows = db.query(Tender).all()
    records = []
    for t in rows:
        records.append({
            "tender_id": t.tender_id or "—",
            "title": t.title or "Untitled",
            "organization": t.organization or "—",
            "tender_type": t.tender_type or "—",
            "budget": t.budget or "—",
            "deadline": t.deadline or "—",
            "emd_amount": t.emd_amount or "—",
            "risk_level": t.risk_level or "—",
            "match_score": t.match_score or "0",
            "recommendation": t.recommendation or "—",
            "summary": t.summary or "",
            "reason": t.match_reason or "—",
            "required_experience": t.required_experience or "—",
            "eligibility": t.eligibility_criteria or "—",
        })
    db.close()
    return pd.DataFrame(records)

try:
    df = load_tenders()
    df['score_num'] = pd.to_numeric(df['match_score'], errors='coerce').fillna(0)
except Exception as e:
    st.error(f"❌ Database error: {e}")
    df = pd.DataFrame()

# ── Empty State ───────────────────────────────────────────────────────────────
if df.empty:
    st.markdown("""
    <div style="text-align:center;padding:80px 20px;">
        <h2>📭 No Tenders in Database Yet</h2>
        <p style="color:#8888bb;font-size:1.1rem;max-width:500px;margin:auto;">
            Click <strong>🚀 Fetch Now from CPPP</strong> in the sidebar to scrape live tenders
            from the government portal and populate this dashboard.
        </p>
        <br>
        <p style="color:#6666aa;">Or run from terminal:<br>
        <code style="background:#1a1a35;padding:8px 16px;border-radius:8px;">
        uv run python cppp_bulk_fetch.py "" 2</code></p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# ── Apply Filters ─────────────────────────────────────────────────────────────
filtered = df.copy()

if risk_opts:
    filtered = filtered[filtered['risk_level'].str.contains('|'.join(risk_opts), case=False, na=False)]

filtered = filtered[filtered['score_num'] >= min_score]

if search_q:
    mask = (
        filtered['title'].str.contains(search_q, case=False, na=False) |
        filtered['tender_type'].str.contains(search_q, case=False, na=False) |
        filtered['summary'].str.contains(search_q, case=False, na=False) |
        filtered['organization'].str.contains(search_q, case=False, na=False)
    )
    filtered = filtered[mask]

if semantic_q:
    try:
        vdb = get_vector_db()
        results = vdb.semantic_search(semantic_q, n_results=10)
        
        # Get IDs from vector DB search
        if results and "ids" in results and results["ids"] and len(results["ids"][0]) > 0:
            matched_ids = results["ids"][0]
            # Filter the dataframe to only include matched IDs
            filtered = filtered[filtered['tender_id'].isin(matched_ids)]
        else:
            # If search returns empty, clear the table
            filtered = filtered.iloc[0:0]
            st.warning("No semantic matches found.")
    except Exception as e:
        st.error(f"Semantic search failed: {e}")

# Sort
if sort_by == "Match Score ↓":
    filtered = filtered.sort_values('score_num', ascending=False)
elif sort_by == "Match Score ↑":
    filtered = filtered.sort_values('score_num', ascending=True)
elif sort_by == "Recommendation":
    filtered = filtered.sort_values('recommendation')

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["📋 Tenders", "📊 Analytics", "🔔 Notifications"])

# ════════════════════════════════════════════════════════════════════════════════
# TAB 1 — TENDERS
# ════════════════════════════════════════════════════════════════════════════════
with tab1:
    # Metrics
    go_count = int(
        (filtered['recommendation'].str.lower().str.contains("go", na=False) &
         ~filtered['recommendation'].str.lower().str.contains("no-go", na=False)).sum()
    )
    high_risk = int(filtered['risk_level'].str.contains("High", case=False, na=False).sum())
    avg_score = int(filtered['score_num'].mean()) if not filtered.empty else 0
    total = len(filtered)

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("📄 Total Tenders", total)
    m2.metric("✅ Go Decision", go_count)
    m3.metric("🔴 High Risk", high_risk)
    m4.metric("🎯 Avg Score", f"{avg_score}%")
    m5.metric("📊 In DB Total", len(df))

    st.divider()
    st.subheader(f"📄 Ranked Tenders — {total} results")

    if filtered.empty:
        st.warning("No tenders match your filters. Adjust the sidebar filters or fetch more data.")

    for _, row in filtered.iterrows():
        score = row['score_num']
        risk_str = str(row['risk_level']).lower()

        if "high" in risk_str:
            risk_class, border = "high", "#f44336"
        elif "medium" in risk_str:
            risk_class, border = "medium", "#ff9800"
        else:
            risk_class, border = "low", "#4CAF50"

        score_color = "#4CAF50" if score >= 70 else ("#ff9800" if score >= 40 else "#f44336")
        rec = str(row['recommendation'])
        rec_icon = "✅" if "go" in rec.lower() and "no" not in rec.lower() else "❌"

        st.markdown(f"""
        <div class="tender-card {risk_class}">
            <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:10px;">
                <div style="flex:1;min-width:200px;">
                    <h3 style="margin:0 0 4px 0;font-size:1rem;">{row['title'][:100]}</h3>
                    <p style="color:#8888bb;margin:0;font-size:0.8rem;">
                        🏢 {row['organization']} &nbsp;|&nbsp; 🆔 {row['tender_id']}
                    </p>
                </div>
                <div class="score-pill" style="color:{score_color};border:2px solid {score_color};background:rgba(0,0,0,0.3);">
                    {int(score)}% Match
                </div>
            </div>
            <hr style="border-color:#1e1e4a;margin:12px 0;">
            <div style="display:flex;flex-wrap:wrap;gap:16px;font-size:0.88rem;">
                <span>💰 <strong>Budget:</strong> {row['budget']}</span>
                <span>📋 <strong>EMD:</strong> {row['emd_amount']}</span>
                <span>📅 <strong>Deadline:</strong> {row['deadline']}</span>
                <span>⚠️ <strong>Risk:</strong> {row['risk_level']}</span>
                <span>🏷️ <strong>Type:</strong> {row['tender_type']}</span>
            </div>
            <p style="margin:10px 0 4px 0;font-size:0.9rem;">{rec_icon} <strong>{row['recommendation']}</strong> — {row['reason']}</p>
            <p style="color:#aaaacc;font-size:0.82rem;margin:4px 0 0 0;">{row['summary']}</p>
        </div>
        """, unsafe_allow_html=True)
        
        with st.expander(f"🔍 View Full AI Analysis — {row['tender_id']}"):
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("#### Requirements")
                st.write(f"**Experience Required:** {row['required_experience']}")
                st.write(f"**Eligibility Criteria:** {row['eligibility']}")
            with c2:
                st.markdown("#### Strategic Insights")
                st.write(f"**Reasoning:** {row['reason']}")
                st.write(f"**Recommendation:** {row['recommendation']}")
                st.write(f"**Match Score:** {int(score)}/100")
            
            st.markdown(f"🔗 [Search this tender on CPPP](https://eprocure.gov.in/cppp/tendersearch)")

# ════════════════════════════════════════════════════════════════════════════════
# TAB 2 — ANALYTICS
# ════════════════════════════════════════════════════════════════════════════════
with tab2:
    st.subheader("📊 Tender Analytics Dashboard")

    a1, a2 = st.columns(2)
    with a1:
        st.markdown("#### Risk Distribution")
        risk_counts = df['risk_level'].value_counts()
        st.bar_chart(risk_counts, color="#a78bfa")

    with a2:
        st.markdown("#### Match Score Buckets")
        buckets = pd.cut(df['score_num'], bins=[0, 30, 50, 70, 90, 100],
                         labels=["0–30%", "31–50%", "51–70%", "71–90%", "91–100%"])
        st.bar_chart(buckets.value_counts().sort_index(), color="#4CAF50")

    a3, a4 = st.columns(2)
    with a3:
        st.markdown("#### Recommendations")
        rec_counts = df['recommendation'].value_counts()
        st.bar_chart(rec_counts, color="#f59e0b")

    with a4:
        st.markdown("#### Top Tender Types")
        type_counts = df['tender_type'].value_counts().head(8)
        st.bar_chart(type_counts, color="#06b6d4")

    st.divider()
    st.subheader("📋 Raw Data Table")
    display_cols = ['tender_id', 'title', 'tender_type', 'risk_level', 'match_score', 'recommendation', 'deadline']
    st.dataframe(filtered[display_cols].reset_index(drop=True), use_container_width=True)

    csv = filtered.to_csv(index=False).encode('utf-8')
    st.download_button("⬇️ Download CSV Report", csv, "tenders_report.csv", "text/csv")

# ════════════════════════════════════════════════════════════════════════════════
# TAB 3 — NOTIFICATIONS LOG
# ════════════════════════════════════════════════════════════════════════════════
with tab3:
    st.subheader("🔔 Smart Notifications Log")

    col_n1, col_n2 = st.columns(2)

    with col_n1:
        st.markdown("#### Alert Log (`notifications.log`)")
        if NOTIF_FILE.exists():
            content = NOTIF_FILE.read_text(encoding="utf-8").strip()
            if content:
                st.markdown(f'<div class="log-box">{content[-3000:]}</div>', unsafe_allow_html=True)
            else:
                st.info("No notifications yet. Run the pipeline to generate alerts.")
        else:
            st.info("Notifications file not found. Run the pipeline first.")

    with col_n2:
        st.markdown("#### Scheduler Log (`scheduler.log`)")
        if LOG_FILE.exists():
            sched_content = LOG_FILE.read_text(encoding="utf-8").strip()
            if sched_content:
                st.markdown(f'<div class="log-box">{sched_content[-3000:]}</div>', unsafe_allow_html=True)
            else:
                st.info("Scheduler hasn't run yet.")
        else:
            st.info("Start `run_scheduler.bat` to begin automated fetching.")

    st.divider()

    # High priority alerts at a glance
    st.markdown("#### 🚀 High Priority Tenders (Score ≥ 70)")
    high_priority = df[df['score_num'] >= 70].sort_values('score_num', ascending=False)
    if not high_priority.empty:
        for _, row in high_priority.iterrows():
            st.success(f"**{row['title'][:80]}** — Score: {row['match_score']}% | {row['recommendation']} | Risk: {row['risk_level']}")
    else:
        st.info("No high-priority tenders found yet.")

st.divider()
st.markdown(
    "<p style='text-align:center;color:#444;font-size:0.75rem;'>"
    "Tender Intelligence System — CPPP Portal Integration — Powered by CrewAI & OpenRouter</p>",
    unsafe_allow_html=True
)
