import streamlit as st
import requests
import pandas as pd
from io import BytesIO
import json

API_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="Bug Deduplication App",
                   layout="wide", page_icon="🐞")

st.title("🐞 Bug Deduplication App - Qdrant Multi-Collection")

# --- API Helper ---


@st.cache_data(ttl=30)
def get_all_collections():
    try:
        response = requests.get(f"{API_URL}/vector-store/collections")
        if response.status_code == 200:
            return response.json()
        return []
    except:
        return []


def api_call(endpoint, method="GET", data=None, files=None):
    try:
        if method == "GET":
            response = requests.get(f"{API_URL}{endpoint}")
        elif method == "POST":
            if files:
                response = requests.post(f"{API_URL}{endpoint}", files=files)
            else:
                response = requests.post(f"{API_URL}{endpoint}", json=data)
        elif method == "DELETE":
            response = requests.delete(f"{API_URL}{endpoint}")

        if response.status_code in [200, 201]:
            return response.json()
        st.error(f"API {response.status_code}: {response.text}")
        return None
    except Exception as e:
        st.error(f"Connection error: {e}")
        return None


def safe_status(product: str):
    """Safe status with fallback"""
    status = api_call(f"/vector-store/collection/{product}/status")
    return status or {"total_issues": 0, "index_built": False, "collection_name": product}


# --- Sidebar ---
st.sidebar.title("⚙️ Product")
collections = get_all_collections()
if collections:
    product_name = st.sidebar.selectbox(
        "Select Collection",
        [c['name'] for c in collections]
    )
else:
    product_name = st.sidebar.text_input(
        "Product Name", value="android_mda_connect")

page = st.sidebar.radio(
    "Navigation", ["📊 Collections", "📈 Append Issues", "🔍 Dedup New"])

# --- Collections ---
if page == "📊 Collections":
    st.header("🗂️ Manage Collections")

    collections = get_all_collections()
    if not collections:
        st.info("👆 Create first collection in Append Issues tab")
        st.stop()

    # Table
    df = pd.DataFrame(collections)
    st.dataframe(df, use_container_width=True)

    # Actions
    col1, col2 = st.columns(2)
    with col1:
        new_coll = st.text_input("New Collection")
        if st.button("➕ Create") and new_coll:
            result = api_call(
                f"/vector-store/collection/create?product_name={new_coll}", "POST")
            if result:
                st.success(f"✅ {new_coll} created!")
                st.rerun()

    with col2:
        del_coll = st.selectbox(
            "Delete", [""] + [c['name'] for c in collections])
        if st.button("🗑️ Delete") and del_coll:
            result = api_call(f"/vector-store/collection/{del_coll}", "DELETE")
            if result:
                st.success(f"✅ {del_coll} deleted!")
                st.rerun()

# --- Append Issues ---
elif page == "📈 Append Issues":
    st.header(f"📦 Append to **{product_name}**")

    status = safe_status(product_name)
    col1, col2 = st.columns(2)
    col1.metric("Current Issues", status["total_issues"])
    col2.metric("Ready", "✅" if status["index_built"] else "⚠️")

    tab1, tab2 = st.tabs(["📁 File", "📄 JSON"])

    with tab1:
        uploaded = st.file_uploader(
            "Reference Issues CSV/Excel", ["csv", "xlsx"])
        if uploaded and st.button("➕ Append", type="primary"):
            with st.spinner("Uploading..."):
                files = {
                    "file": (uploaded.name, uploaded.getvalue(), uploaded.type)}
                result = api_call("/vector-store/append", "POST", files=files)
                if result:
                    st.success(f"✅ +{result['issues_added']} issues!")
                    st.rerun()

    with tab2:
        json_str = st.text_area("JSON Issues", height=200)
        if st.button("➕ Append JSON"):
            try:
                data = json.loads(json_str)
                result = api_call("/vector-store/append-json", "POST", data)
                if result:
                    st.success(f"✅ +{result['issues_added']}!")
                    st.rerun()
            except:
                st.error("Invalid JSON")

# --- Dedup ---
elif page == "🔍 Dedup New":
    st.header(f"🎯 Dedup vs **{product_name}**")

    status = safe_status(product_name)
    if status["total_issues"] == 0:
        st.warning("⚠️ No reference issues. Append first!")
        st.stop()

    st.info(f"**Matching against {status['total_issues']} reference issues**")

    tab1, tab2 = st.tabs(["Excel", "JSON"])

    with tab1:
        uploaded = st.file_uploader("New Issues Excel", ["xlsx"])
        if uploaded:
            if st.button("🚀 Process", type="primary"):
                with st.spinner("Analysis..."):
                    files = {"file": uploaded.getvalue()}
                    resp = requests.post(
                        f"{API_URL}/process-excel?product_name={product_name}",
                        files=files
                    )
                    if resp.status_code == 200:
                        st.success("✅ Done!")
                        st.download_button(
                            "💾 Download",
                            resp.content,
                            f"deduped_{product_name}_{uploaded.name}",
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                    else:
                        st.error(resp.text)

    with tab2:
        # JSON Builder
        bugs = []
        for i in range(3):
            with st.expander(f"New Bug #{i+1}"):
                bug_id = st.text_input("ID", key=f"id{i}")
                title = st.text_input("Title", key=f"t{i}")
                steps = st.text_area("Steps", height=80, key=f"s{i}")
                mod = st.text_input("Module", key=f"m{i}")
                if title and steps:
                    bugs.append({"id": bug_id or f"NEW_{i}", "product": product_name,
                                "title": title, "repro_steps": steps, "module": mod})

        if bugs and st.button("🔍 Analyze", type="primary"):
            payload = {"product_name": product_name, "bug_reports": bugs}
            resp = requests.post(f"{API_URL}/process-json", json=payload)
            if resp.status_code == 200:
                results = resp.json()
                st.success(f"✅ {len(results)} analyzed!")
                df = pd.json_normalize(results)
                st.dataframe(df)
                st.download_button("💾 JSON", json.dumps(
                    results, indent=2), f"results_{product_name}.json")
            else:
                st.error(resp.text)

st.markdown("---")
st.caption("FastAPI + Qdrant | v2.12.5")
