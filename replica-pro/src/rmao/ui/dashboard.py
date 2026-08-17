import streamlit as st
import requests
import os
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(page_title="Replica-Pro Dashboard", layout="wide")

st.title("🤖 Replica-Pro Orchestrator Dashboard")
st.markdown("---")

# Sidebar for authentication
with st.sidebar:
    st.header("⚙️ Configuration")
    api_key = st.text_input("API Key (optional)", type="password")
    github_owner = st.text_input("GitHub Owner", value=os.getenv("GITHUB_OWNER", ""))
    mode = st.radio("Mode", ["Mock", "Real"], index=0)

# Main area: Trigger Build
st.header("🚀 Trigger New Build")
col1, col2 = st.columns([3, 1])
with col1:
    project_idea = st.text_area("Project Idea", "Build a simple e-commerce website with payment")
with col2:
    tasks = st.number_input("Number of Tasks", min_value=2, max_value=4, value=4)
    run_btn = st.button("Run Orchestrator", type="primary", use_container_width=True)

if run_btn and project_idea:
    with st.spinner("Orchestrator running..."):
        payload = {
            "query": project_idea,
            "tasks": tasks,
            "mode": "mock" if mode == "Mock" else "real"
        }
        headers = {}
        if api_key:
            headers["X-API-Key"] = api_key
        
        try:
            resp = requests.post(f"{API_URL}/v1/run", json=payload, headers=headers, timeout=60)
            if resp.status_code == 200:
                data = resp.json()
                st.success(f"✅ Build successful! Repo: {data.get('repo_url')}")
                st.json(data)
            else:
                st.error(f"❌ Error {resp.status_code}: {resp.text}")
        except Exception as e:
            st.error(f"Connection error: {e}")

# Status placeholder
st.header("📊 Recent Runs")
st.info("Integration with database/logging pending... (Showing mock data)")
st.dataframe({
    "Run ID": ["run-001", "run-002"],
    "Status": ["✅ Completed", "⚠️ Failed"],
    "Repo": ["https://github.com/test/demo", "https://github.com/test/error"],
})
