import streamlit as st
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ui_components import setup_page, render_header, load_company_profile, PROFILE_FILE

setup_page("Company Profile")
render_header("Company Profile", "Define your capabilities to power the AI ranking engine")

profile = load_company_profile()

with st.form("company_profile_form"):
    st.markdown("#### General Information")
    col1, col2 = st.columns(2)
    with col1:
        c_name = st.text_input("Company Name", value=profile.get("company_name", ""))
        c_exp  = st.number_input("Years of Experience", min_value=0, value=profile.get("experience_years", 0))
    with col2:
        c_turn = st.number_input("Annual Turnover (Crore ₹)", min_value=0.0, value=float(profile.get("annual_turnover_crore", 0.0)))
        c_emp  = st.number_input("Number of Employees", min_value=0, value=profile.get("employee_count", 0))
    
    st.markdown("#### Capabilities & Limits")
    col3, col4 = st.columns(2)
    with col3:
        c_max_proj = st.number_input("Max Project Value (Crore ₹)", min_value=0.0, value=float(profile.get("max_project_value_crore", 0.0)))
    with col4:
        c_max_emd  = st.number_input("Max EMD Capacity (Lakh ₹)", min_value=0.0, value=float(profile.get("max_emd_capacity_lakh", 0.0)))
    
    st.markdown("#### Specialization")
    existing_specs = "\n".join(profile.get("specialization", []))
    c_specs = st.text_area("Areas of Expertise (One per line)", value=existing_specs, height=150)
    
    existing_certs = "\n".join(profile.get("certifications", []))
    c_certs = st.text_area("Certifications (ISO, CMMI, etc. One per line)", value=existing_certs, height=100)
    
    submitted = st.form_submit_button("💾 Save Profile", use_container_width=True)
    
    if submitted:
        new_profile = {
            "company_name": c_name,
            "experience_years": c_exp,
            "annual_turnover_crore": c_turn,
            "employee_count": c_emp,
            "max_project_value_crore": c_max_proj,
            "max_emd_capacity_lakh": c_max_emd,
            "specialization": [s.strip() for s in c_specs.split("\n") if s.strip()],
            "certifications": [c.strip() for c in c_certs.split("\n") if c.strip()],
        }
        try:
            with open(PROFILE_FILE, "w", encoding="utf-8") as f:
                json.dump(new_profile, f, indent=4)
            st.success("Company profile saved successfully! AI matching will now use these updated parameters.")
        except Exception as e:
            st.error(f"Error saving profile: {e}")
