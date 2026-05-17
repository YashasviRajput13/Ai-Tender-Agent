import streamlit as st
import pandas as pd
import sys
import os

# Fix relative imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ui_components import setup_page, render_header, load_tenders, get_score_color

setup_page("Tender Explorer")
render_header("Tender Explorer", "Search, filter, and drill down into tender data")

df = load_tenders()

if df.empty:
    st.info("Database is empty. Please run a fetch from the Dashboard.")
    st.stop()

# ── Filters ────────────────────────────────────────────────────────
with st.expander("Advanced Filters", expanded=True):
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        search_q = st.text_input("Semantic Search", placeholder="e.g. IT software...")
    with col2:
        type_opts = ["All"] + sorted(df["tender_type"].dropna().unique().tolist())
        sel_type = st.selectbox("Tender Type", type_opts)
    with col3:
        risk_opts = ["All", "Low", "Medium", "High"]
        sel_risk = st.selectbox("Risk Level", risk_opts)
    with col4:
        rec_opts = ["All", "Go", "Review", "No-Go"]
        sel_rec = st.selectbox("Recommendation", rec_opts)

# Apply filters
filtered = df.copy()
if search_q:
    m = (filtered["title"].str.contains(search_q, case=False, na=False) |
         filtered["summary"].str.contains(search_q, case=False, na=False) |
         filtered["organization"].str.contains(search_q, case=False, na=False))
    filtered = filtered[m]
if sel_type != "All":
    filtered = filtered[filtered["tender_type"] == sel_type]
if sel_risk != "All":
    filtered = filtered[filtered["risk_level"].str.contains(sel_risk, case=False, na=False)]
if sel_rec != "All":
    filtered = filtered[filtered["recommendation"] == sel_rec]

st.markdown(f"**{len(filtered)} results found**")

# ── Data Feed ────────────────────────────────────────────────────────
for _, row in filtered.iterrows():
    sc = row["score_num"]
    risk_str = str(row["risk_level"]).lower()
    risk_class = "high" if "high" in risk_str else ("medium" if "medium" in risk_str else "low")
    sc_color   = get_score_color(sc)
    rec        = str(row["recommendation"])
    rec_icon   = "✅" if rec == "Go" else ("⚠️" if rec == "Review" else "❌")
    risk_badge = f'<span class="risk-{risk_class}">{row["risk_level"]}</span>'

    st.markdown(f"""
    <div class="tender-card {risk_class}">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:12px;">
        <div style="flex:1;min-width:220px;">
          <div style="font-weight:700;font-size:0.97rem;color:#EDEDED;margin-bottom:4px;">{row["title"]}</div>
          <div style="color:#888888;font-size:0.8rem;">
            🏢 {row["organization"]} &nbsp;·&nbsp; 🆔 {row["tender_id"]}
          </div>
        </div>
        <div style="display:flex;align-items:center;gap:10px;">
          {risk_badge}
          <span class="score-badge" style="color:{sc_color};border-color:{sc_color};">{int(sc)}%</span>
        </div>
      </div>
      <div style="display:flex;flex-wrap:wrap;gap:18px;font-size:0.85rem;margin:12px 0;color:#A3A3A3;">
        <span>💰 <strong>Budget:</strong> {row["budget"]}</span>
        <span>📋 <strong>EMD:</strong> {row["emd_amount"]}</span>
        <span>📅 <strong>Deadline:</strong> {row["deadline"]}</span>
        <span>🏷️ <strong>Type:</strong> {row["tender_type"]}</span>
      </div>
      <div style="font-size:0.88rem;color:#D1D5DB;font-weight:600;">{rec_icon} {rec} — <span style="color:#9CA3AF;font-weight:400;">{row["reason"][:120]}...</span></div>
    </div>
    """, unsafe_allow_html=True)

    with st.expander("🔍 View Full Details"):
        st.write(f"**Summary:** {row['summary']}")
        ea, eb, ec = st.columns(3)
        with ea:
            st.markdown("**📋 Requirements**")
            st.write(f"**Experience:** {row['required_experience']}")
            st.write(f"**Eligibility:** {row['eligibility']}")
        with eb:
            st.markdown("**📊 Financial**")
            st.write(f"**Budget:** {row['budget']}")
            st.write(f"**EMD:** {row['emd_amount']}")
            st.write(f"**Deadline:** {row['deadline']}")
        with ec:
            st.markdown("**🎯 Decision**")
            st.write(f"**Score:** {int(sc)}/100")
            st.write(f"**Recommendation:** {rec}")
            st.write(f"**Risk:** {row['risk_level']}")
        if row["detail_url"] and str(row["detail_url"]).startswith("http"):
            st.markdown(f"[🔗 Open on CPPP Portal]({row['detail_url']})")
