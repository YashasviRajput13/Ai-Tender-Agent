import streamlit as st
import pandas as pd
import subprocess
import os
import sys
from pathlib import Path
from ui_components import setup_page, render_header, load_tenders

# Must be called first
setup_page("Enterprise Dashboard")

PROJECT_DIR = Path(__file__).parent
FETCH_SCRIPT = PROJECT_DIR / "cppp_bulk_fetch.py"

render_header("Overview", "High-level metrics and system status")

df = load_tenders()

db_tot = len(df)
go_cnt = len(df[df["recommendation"] == "Go"]) if not df.empty else 0
hi_cnt = len(df[df["risk_level"] == "High"]) if not df.empty else 0
avg_sc = int(df["score_num"].mean()) if not df.empty else 0

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Indexed", db_tot)
col2.metric("Recommended (Go)", go_cnt)
col3.metric("High Risk Tenders", hi_cnt)
col4.metric("Avg Match Score", f"{avg_sc}%")

st.markdown("<br>", unsafe_allow_html=True)

# ── Live Fetch Actions ────────────────────────────────────────────────────────
st.markdown("### Quick Actions")
with st.container(border=True):
    colA, colB, colC = st.columns([2, 1, 1])
    with colA:
        fetch_keyword = st.text_input("Keyword filter (e.g., Road, IT, Water)", placeholder="Leave blank for all")
    with colB:
        fetch_pages = st.number_input("Pages to Scrape", min_value=1, max_value=50, value=2)
    with colC:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🚀 Run Live Fetch", use_container_width=True):
            with st.status("Fetching live data from CPPP & running AI analysis...", expanded=True) as status:
                st.write(f"Executing `cppp_bulk_fetch.py '{fetch_keyword}' {fetch_pages}`")
                
                env = os.environ.copy()
                env["PYTHONUTF8"] = "1"
                env["PYTHONIOENCODING"] = "utf-8"
                result = subprocess.run(
                    [sys.executable, str(FETCH_SCRIPT), fetch_keyword, str(fetch_pages)],
                    cwd=PROJECT_DIR, capture_output=True, text=True,
                    encoding="utf-8", errors="replace", timeout=240, env=env,
                )
                
                if result.stdout:
                    st.code(result.stdout)
                if result.stderr:
                    st.code(result.stderr)
                
                if result.returncode == 0:
                    status.update(label="Fetch Complete!", state="complete", expanded=False)
                    st.cache_data.clear()
                    st.rerun()
                else:
                    status.update(label="Fetch Failed", state="error", expanded=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Top Tenders Feed ────────────────────────────────────────────────────────
st.markdown("### Top Recommended Tenders")
if df.empty:
    st.info("No tenders in database. Run a Live Fetch above.")
else:
    # Sort by score desc, take top 3 "Go"
    top_df = df[df["recommendation"] == "Go"].sort_values("score_num", ascending=False).head(5)
    if top_df.empty:
        top_df = df.sort_values("score_num", ascending=False).head(3)

    for _, row in top_df.iterrows():
        sc = row["score_num"]
        risk_str = str(row["risk_level"]).lower()
        risk_class = "high" if "high" in risk_str else ("medium" if "medium" in risk_str else "low")
        sc_color   = "#22c55e" if sc >= 70 else ("#f59e0b" if sc >= 50 else "#ef4444")
        rec        = str(row["recommendation"])
        rec_icon   = "✅" if rec == "Go" else ("⚠️" if rec == "Review" else "❌")
        risk_badge = f'<span class="risk-{risk_class}">{row["risk_level"]}</span>'

        st.markdown(f"""
        <div class="tender-card">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:12px;">
            <div style="flex:1;min-width:220px;">
              <div style="font-weight:600;font-size:1rem;color:#EDEDED;margin-bottom:4px;">{row["title"][:110]}</div>
              <div style="color:#888888;font-size:0.8rem;">
                🏢 {row["organization"]} &nbsp;·&nbsp; 🆔 {row["tender_id"]}
              </div>
            </div>
            <div style="display:flex;align-items:center;gap:10px;">
              {risk_badge}
              <span class="score-badge" style="color:{sc_color};border-color:{sc_color};">{int(sc)}%</span>
            </div>
          </div>
          <div style="display:flex;flex-wrap:wrap;gap:18px;font-size:0.85rem;margin-top:14px;color:#A3A3A3;">
            <span>💰 {row["budget"]}</span>
            <span>📅 {row["deadline"]}</span>
            <span>🏷️ {row["tender_type"]}</span>
          </div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("""
<div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #222; color: #666; font-size: 0.8rem;">
    Navigate to the sidebar to explore analytics, semantic search, AI insights, and settings.
</div>
""", unsafe_allow_html=True)
