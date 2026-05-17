import streamlit as st
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ui_components import setup_page, render_header, load_tenders

setup_page("Notifications")
render_header("Notification Center", "System logs, alerts, and priority matches")

PROJECT_DIR = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
NOTIF_FILE = PROJECT_DIR / "notifications.log"
LOG_FILE = PROJECT_DIR / "scheduler.log"

st.markdown("""
<style>
.log-box {
    background: #0A0A0A;
    border: 1px solid #222222;
    padding: 12px;
    border-radius: 6px;
    height: 300px;
    overflow-y: auto;
    font-family: monospace;
    font-size: 0.8rem;
    color: #A3A3A3;
}
</style>
""", unsafe_allow_html=True)

df = load_tenders()

st.markdown("### 🚀 High-Priority Alerts (Score ≥ 70)")
if not df.empty:
    hi = df[df["score_num"] >= 70].sort_values("score_num", ascending=False)
    if not hi.empty:
        for _, r in hi.head(10).iterrows():
            st.markdown(f"""
            <div class="tender-card">
              <div style="display:flex;justify-content:space-between;align-items:center;">
                <div>
                  <div style="font-weight:600;color:#EDEDED;font-size:0.9rem;">{r["title"][:80]}</div>
                  <div style="color:#888888;font-size:0.78rem;margin-top:2px;">🏢 {r["organization"]}</div>
                </div>
                <div style="text-align:right;">
                  <div style="color:#22c55e;font-weight:700;font-size:1.1rem;">{int(r["score_num"])}%</div>
                  <div style="color:#A3A3A3;font-size:0.75rem;">{r["recommendation"]}</div>
                </div>
              </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No high-priority tenders found currently.")
else:
    st.info("Database is empty.")

st.markdown("<hr>", unsafe_allow_html=True)

n1, n2 = st.columns(2)
with n1:
    st.markdown("#### Alert Log")
    if NOTIF_FILE.exists():
        notif_content = NOTIF_FILE.read_text(encoding="utf-8", errors="replace").strip()
        lines = notif_content.split("\n") if notif_content else []
        st.markdown(f'<div class="log-box">{chr(10).join(lines[-40:])}</div>', unsafe_allow_html=True)
    else:
        st.info("No alerts logged yet.")

with n2:
    st.markdown("#### Scheduler Log")
    if LOG_FILE.exists():
        sched_content = LOG_FILE.read_text(encoding="utf-8", errors="replace").strip()
        lines = sched_content.split("\n") if sched_content else []
        st.markdown(f'<div class="log-box">{chr(10).join(lines[-40:])}</div>', unsafe_allow_html=True)
    else:
        st.info("Scheduler has not run yet.")
