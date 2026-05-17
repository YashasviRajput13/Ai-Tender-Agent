import streamlit as st
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ui_components import setup_page, render_header, load_tenders
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv

load_dotenv()

setup_page("AI Insights")
render_header("AI Assistant", "Ask questions about the indexed tenders and your capabilities")

st.markdown("<br>", unsafe_allow_html=True)

df = load_tenders()

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hello! I am your AI Procurement Assistant. How can I help you analyze the tender database today?"}
    ]

# Display chat messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Chat Input
if prompt := st.chat_input("Ask about tenders, budget trends, or specific capabilities..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Analyzing database..."):
            try:
                # Basic integration with Gemini Flash via OpenRouter
                llm = ChatOpenAI(
                    model_name=os.getenv("AI_MODEL", "google/gemini-flash-1.5"),
                    openai_api_key=os.getenv("OPENROUTER_API_KEY", "dummy"),
                    openai_api_base="https://openrouter.ai/api/v1",
                    max_retries=1
                )
                
                # Create a minimal context of the top 20 tenders to inject into the prompt
                context_df = df.head(20)[["tender_id", "title", "budget", "recommendation", "risk_level"]]
                context_str = context_df.to_csv(index=False)
                
                template = """
                You are an expert AI Procurement Assistant. Use the following context of recently fetched tenders to answer the user's question.
                
                Context (Top Tenders in DB):
                {context}
                
                User Question: {question}
                
                Answer concisely and professionally. If the data isn't in the context, say so.
                """
                prompt_template = PromptTemplate(template=template, input_variables=["context", "question"])
                
                chain = prompt_template | llm
                response = chain.invoke({"context": context_str, "question": prompt})
                reply = response.content
            except Exception as e:
                reply = f"Sorry, I encountered an error while analyzing the data. Ensure OPENROUTER_API_KEY is set. Error: {str(e)}"
            
            st.markdown(reply)
            st.session_state.messages.append({"role": "assistant", "content": reply})
