import streamlit as st
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ui_components import setup_page, render_header, load_tenders

setup_page("Analytics")
render_header("Analytics", "Data-driven insights into procurement opportunities")

df = load_tenders()

if df.empty:
    st.info("No data available for analytics.")
    st.stop()

try:
    import plotly.express as px
    import plotly.graph_objects as go

    PLOT_BG    = "rgba(0,0,0,0)"
    PAPER_BG   = "rgba(0,0,0,0)"
    FONT_COLOR = "#D1D5DB"
    GRID_COLOR = "#222222"

    def style_fig(fig):
        fig.update_layout(
            plot_bgcolor=PLOT_BG, paper_bgcolor=PAPER_BG,
            font_color=FONT_COLOR, margin=dict(l=10,r=10,t=30,b=10),
            legend=dict(bgcolor="rgba(0,0,0,0)"),
        )
        fig.update_xaxes(gridcolor=GRID_COLOR, zeroline=False)
        fig.update_yaxes(gridcolor=GRID_COLOR, zeroline=False)
        return fig

    r1c1, r1c2 = st.columns(2)

    with r1c1:
        st.markdown("<h4 style='font-size:1.1rem;'>Risk Distribution</h4>", unsafe_allow_html=True)
        risk_counts = df["risk_level"].value_counts().reset_index()
        risk_counts.columns = ["Risk", "Count"]
        clr_map = {"High": "#ef4444", "Medium": "#f59e0b", "Low": "#22c55e"}
        fig_risk = px.pie(risk_counts, names="Risk", values="Count",
                          color="Risk", color_discrete_map=clr_map, hole=0.45)
        fig_risk = style_fig(fig_risk)
        fig_risk.update_traces(textfont_size=13, marker=dict(line=dict(color="#000000", width=2)))
        st.plotly_chart(fig_risk, use_container_width=True)

    with r1c2:
        st.markdown("<h4 style='font-size:1.1rem;'>Match Score Distribution</h4>", unsafe_allow_html=True)
        fig_hist = px.histogram(df, x="score_num", nbins=10,
                                color_discrete_sequence=["#EDEDED"],
                                labels={"score_num": "Match Score (%)"})
        fig_hist = style_fig(fig_hist)
        fig_hist.update_traces(marker_line_color="#222222", marker_line_width=1)
        st.plotly_chart(fig_hist, use_container_width=True)

    r2c1, r2c2 = st.columns(2)

    with r2c1:
        st.markdown("<h4 style='font-size:1.1rem;'>Recommendations</h4>", unsafe_allow_html=True)
        rec_counts = df["recommendation"].value_counts().reset_index()
        rec_counts.columns = ["Recommendation", "Count"]
        rec_clr = {"Go": "#22c55e", "Review": "#f59e0b", "No-Go": "#ef4444"}
        fig_rec = px.bar(rec_counts, x="Recommendation", y="Count",
                         color="Recommendation", color_discrete_map=rec_clr, text="Count")
        fig_rec = style_fig(fig_rec)
        fig_rec.update_traces(textposition="outside", textfont_color=FONT_COLOR)
        fig_rec.update_layout(showlegend=False)
        st.plotly_chart(fig_rec, use_container_width=True)

    with r2c2:
        st.markdown("<h4 style='font-size:1.1rem;'>Top Tender Categories</h4>", unsafe_allow_html=True)
        type_counts = df["tender_type"].value_counts().head(8).reset_index()
        type_counts.columns = ["Type", "Count"]
        fig_type = px.bar(type_counts, x="Count", y="Type", orientation="h",
                          color="Count", color_continuous_scale=["#333333", "#888888", "#EDEDED"])
        fig_type = style_fig(fig_type)
        fig_type.update_layout(coloraxis_showscale=False, yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig_type, use_container_width=True)

    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("<h4 style='font-size:1.1rem;'>Match Score vs Budget (Lakh ₹)</h4>", unsafe_allow_html=True)
    df_scatter = df[df["budget_num"] > 0].copy()
    if not df_scatter.empty:
        clr_seq = {"High": "#ef4444", "Medium": "#f59e0b", "Low": "#22c55e"}
        fig_sc = px.scatter(
            df_scatter, x="budget_num", y="score_num",
            color="risk_level", color_discrete_map=clr_seq,
            size="score_num", size_max=20,
            hover_data=["title", "organization", "recommendation"],
            labels={"budget_num": "Budget (Lakh ₹)", "score_num": "Match Score (%)"},
        )
        fig_sc = style_fig(fig_sc)
        st.plotly_chart(fig_sc, use_container_width=True)
    else:
        st.info("Not enough budget data for scatter plot.")

except ImportError:
    st.warning("⚠️ Plotly not installed.")
    st.bar_chart(df["risk_level"].value_counts())
