"""
ui_components.py — Shared CSS and UI components for the Multipage SaaS Dashboard
"""
import streamlit as st
import pandas as pd
import json
from pathlib import Path
import os
import sys

# Ensure root paths are available
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from db import get_db, init_db
from models import Tender

PROFILE_FILE = Path(os.path.dirname(os.path.abspath(__file__))) / "company_profile.json"

def setup_page(page_title="AI Tender Intelligence"):
    """Must be called FIRST in every page script."""
    st.set_page_config(
        page_title=page_title,
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Geist:wght@300;400;500;600;700&display=swap');
    
    /* Global Vercel/Linear Dark Theme */
    *, html, body, .stApp { 
        font-family: 'Geist', sans-serif !important; 
        box-sizing: border-box; 
    }
    
    .stApp { 
        background: #000000 !important; 
        color: #EDEDED; 
    }
    
    /* Top Progress Bar overrides */
    .stProgress > div > div { background: linear-gradient(90deg, #FFFFFF, #888888) !important; }

    /* Sidebar Navigation */
    section[data-testid="stSidebar"] {
        background: #0A0A0A !important;
        border-right: 1px solid #222222 !important;
    }
    .stSidebarNav {
        padding-top: 1rem !important;
    }
    
    /* Metrics */
    div[data-testid="metric-container"] {
        background: rgba(255, 255, 255, 0.03) !important;
        border: 1px solid #222222 !important; 
        border-radius: 8px !important;
        padding: 16px !important; 
        transition: border 0.2s !important;
    }
    div[data-testid="metric-container"]:hover { 
        border-color: #444444 !important; 
    }
    div[data-testid="metric-container"] label { 
        color: #888888 !important; 
        font-size: 0.8rem !important; 
        font-weight: 500 !important;
    }
    div[data-testid="metric-container"] [data-testid="stMetricValue"] { 
        color: #EDEDED !important; 
        font-weight: 600 !important; 
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] { 
        background: transparent !important; 
        gap: 24px !important; 
        border-bottom: 1px solid #222222 !important;
    }
    .stTabs [data-baseweb="tab"] { 
        color: #888888 !important; 
        font-weight: 500 !important; 
        padding-bottom: 12px !important;
        padding-top: 12px !important;
    }
    .stTabs [aria-selected="true"] { 
        color: #EDEDED !important; 
        border-bottom-color: #EDEDED !important; 
    }

    /* Glassmorphism Cards */
    .tender-card {
        background: rgba(255,255,255,0.02);
        border: 1px solid #222222;
        border-radius: 8px; 
        padding: 20px; 
        margin-bottom: 16px;
        transition: all 0.2s ease;
        position: relative; 
        overflow: hidden;
    }
    .tender-card:hover { 
        background: rgba(255,255,255,0.04);
        border-color: #444444; 
    }
    
    /* Risk Badges */
    .risk-high   { background: rgba(239,68,68,0.1); color: #ef4444; border: 1px solid rgba(239,68,68,0.2); padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 500; }
    .risk-medium { background: rgba(245,158,11,0.1); color: #f59e0b; border: 1px solid rgba(245,158,11,0.2); padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 500; }
    .risk-low    { background: rgba(34,197,94,0.1);  color: #22c55e; border: 1px solid rgba(34,197,94,0.2);  padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 500; }

    /* Score Pill */
    .score-badge {
        font-size: 0.85rem; font-weight: 600; padding: 4px 10px;
        border-radius: 4px; display: inline-block;
        background: rgba(255,255,255,0.05);
        border: 1px solid #333333;
    }

    /* Buttons */
    .stButton > button {
        background: #EDEDED !important;
        color: #000000 !important; 
        border: 1px solid #EDEDED !important;
        border-radius: 6px !important; 
        font-weight: 500 !important;
        padding: 0.4rem 1rem !important; 
        transition: all 0.2s !important;
    }
    .stButton > button:hover {
        background: #FFFFFF !important;
        opacity: 0.9 !important;
    }
    
    /* Secondary buttons (use primary=False in st.button) */
    .stButton > button[kind="secondary"] {
        background: #000000 !important;
        color: #EDEDED !important;
        border: 1px solid #333333 !important;
    }
    .stButton > button[kind="secondary"]:hover {
        background: #111111 !important;
        border-color: #666666 !important;
    }

    /* Inputs */
    .stTextInput > div > div > input, .stSelectbox > div > div { 
        background: rgba(255,255,255,0.02) !important; 
        border: 1px solid #333333 !important; 
        color: #EDEDED !important; 
        border-radius: 6px !important;
    }
    .stTextInput > div > div > input:focus, .stSelectbox > div > div:focus {
        border-color: #666666 !important;
        box-shadow: none !important;
    }
    .stMultiSelect > div > div { background: rgba(255,255,255,0.02) !important; border: 1px solid #333333 !important; border-radius: 6px !important; }
    
    /* Expanders */
    .stExpander { 
        background: transparent !important; 
        border: 1px solid #222222 !important; 
        border-radius: 6px !important; 
    }

    /* Headings */
    h1, h2, h3, h4, h5, h6 { color: #EDEDED !important; font-weight: 600 !important; letter-spacing: -0.02em !important; }
    hr { border-color: #222222 !important; margin: 2rem 0 !important; }
    
    /* Header Bar */
    .page-header {
        border-bottom: 1px solid #222222;
        padding-bottom: 1rem;
        margin-bottom: 2rem;
    }
    .page-title {
        font-size: 1.8rem;
        font-weight: 600;
        letter-spacing: -0.03em;
        margin: 0;
        color: #EDEDED;
    }
    .page-subtitle {
        color: #888888;
        font-size: 0.9rem;
        margin-top: 4px;
    }
    
    /* Chat bubbles */
    [data-testid="stChatMessage"] {
        background: rgba(255,255,255,0.02);
        border: 1px solid #222222;
        border-radius: 8px;
    }
    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] p {
        color: #D1D5DB !important;
    }
    </style>
    """, unsafe_allow_html=True)


@st.cache_data(ttl=60)
def load_tenders():
    """Load tenders with 60s cache to keep UI extremely fast."""
    init_db()
    db = next(get_db())
    rows = db.query(Tender).all()
    records = []
    for t in rows:
        score_raw = t.match_score or "0"
        try:
            score_num = float(score_raw)
        except Exception:
            score_num = 0.0
        records.append({
            "tender_id":    t.tender_id or "—",
            "title":        t.title or "Untitled",
            "organization": t.organization or "—",
            "department":   t.department or t.organization or "—",
            "tender_type":  t.tender_type or "—",
            "budget":       t.budget or "—",
            "budget_num":   t.budget_numeric or 0.0,
            "deadline":     t.deadline or "—",
            "emd_amount":   t.emd_amount or "—",
            "risk_level":   t.risk_level or "—",
            "match_score":  score_raw,
            "score_num":    score_num,
            "recommendation": t.recommendation or "—",
            "summary":      t.summary or "",
            "reason":       t.match_reason or "—",
            "required_experience": t.required_experience or "—",
            "eligibility":  t.eligibility_criteria or "—",
            "published_date": t.published_date or "—",
            "closing_date": t.closing_date or "—",
            "detail_url":   t.detail_url or "",
            "status":       t.status or "active",
            "created_at":   str(t.created_at or ""),
        })
    db.close()
    return pd.DataFrame(records)


def load_company_profile():
    """Load company profile."""
    try:
        with open(PROFILE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"company_name": "Company Not Configured"}


def render_header(title, subtitle=""):
    """Render a consistent page header."""
    st.markdown(f"""
    <div class="page-header">
        <h1 class="page-title">{title}</h1>
        <div class="page-subtitle">{subtitle}</div>
    </div>
    """, unsafe_allow_html=True)


def get_score_color(score):
    return "#22c55e" if score >= 70 else ("#f59e0b" if score >= 50 else "#ef4444")
