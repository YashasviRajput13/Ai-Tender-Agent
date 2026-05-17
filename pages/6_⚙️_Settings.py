import streamlit as st
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ui_components import setup_page, render_header

setup_page("Settings")
render_header("System Settings", "Configure application behavior and environment variables")

st.markdown("### Environment Configuration")
with st.container(border=True):
    ai_model = os.getenv('AI_MODEL', 'google/gemini-flash-1.5')
    api_key_set = bool(os.getenv('OPENROUTER_API_KEY'))
    pdf_enabled = os.getenv('ENABLE_PDF_DOWNLOAD', 'false')
    
    st.write(f"**AI Model in use:** `{ai_model}`")
    if api_key_set:
        st.success("✅ OpenRouter API Key is configured.")
    else:
        st.error("❌ OpenRouter API Key is missing. Tenders will not be analyzed.")
        
    st.write(f"**PDF Extraction Pipeline:** `{'Enabled' if pdf_enabled.lower() == 'true' else 'Disabled'}`")
    
    st.markdown("#### Email Alerts")
    smtp_email = os.getenv("SMTP_EMAIL", "")
    if smtp_email and os.getenv("SMTP_PASSWORD") and os.getenv("ALERT_RECIPIENT"):
        st.success(f"✅ Email alerts active routing to: `{os.getenv('ALERT_RECIPIENT')}`")
    else:
        st.warning("⚠️ Email alerts not configured. Please check `.env` file.")

st.markdown("### Application Cache")
with st.container(border=True):
    st.markdown("If you recently fetched new data or changed your company profile but the changes aren't reflecting, clear the application cache.")
    if st.button("🗑️ Clear Streamlit Cache", use_container_width=True):
        st.cache_data.clear()
        st.success("Cache cleared successfully!")
        
st.markdown("""
<div style="margin-top: 50px; font-size: 0.8rem; color: #666; text-align: center;">
    AI Tender Intelligence Platform v2.0 <br>
    Built with Streamlit, Python, and CrewAI
</div>
""", unsafe_allow_html=True)
