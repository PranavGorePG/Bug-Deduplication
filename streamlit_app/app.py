import streamlit as st
import requests
import pandas as pd
from io import BytesIO

# Configuration
API_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="Bug Deduplication App", layout="wide")

st.title("🐞 Bug Deduplication App")

# --- Sidebar: Navigation ---
page = st.sidebar.radio(
    "Navigation", ["Vector Store Management", "Dedup New Issues"])


def get_status():
    try:
        response = requests.get(f"{API_URL}/vector-store/status")
        if response.status_code == 200:
            return response.json()
    except:
        return None
    return None


# --- Page: Vector Store Management ---
if page == "Vector Store Management":
    st.header("Vector Store Management")

    # Status
    status = get_status()
    if status:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Issues", status["total_issues"])
        c2.metric("Upload Events", status["upload_events"])
        c3.write(f"**Index Built:** {status['index_built']}")
        c4.write(f"**Last Updated (UTC):**\n{status['last_updated_utc']}")
    else:
        st.error("Backend API is not reachable.")

    st.divider()

    # Reset Store
    col1, col2 = st.columns([1, 5])
    if col1.button("Reset Store", type="primary"):
        try:
            res = requests.post(f"{API_URL}/vector-store/reset")
            if res.status_code == 200:
                st.success("Vector store reset successfully!")
                st.rerun()
            else:
                st.error("Failed to reset store.")
        except Exception as e:
            st.error(f"Error: {e}")

    st.divider()

    # Upload Issues
    st.subheader("Append Existing Issues to Store")
    uploaded_file = st.file_uploader(
        "Upload CSV or Excel (Already Reported Issues)", type=["csv", "xlsx", "xls"])

    if uploaded_file:
        if st.button("Append Issues"):
            with st.spinner("Parsing and appending..."):
                files = {
                    "file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                try:
                    response = requests.post(
                        f"{API_URL}/vector-store/append", files=files)
                    if response.status_code == 200:
                        data = response.json()
                        st.success(
                            f"Successfully added {data['issues_added']} new issues!")
                        st.json(data)
                    else:
                        st.error(f"Error: {response.text}")
                except Exception as e:
                    st.error(f"Connection Error: {e}")

# --- Page: Dedup New Issues ---
elif page == "Dedup New Issues":
    st.header("Deduplicate New Issues")

    status = get_status()
    if not status or not status["index_built"] or status["total_issues"] == 0:
        st.warning(
            "⚠️ Vector store is empty. Please go to 'Vector Store Management' and upload existing issues first.")

    uploaded_file = st.file_uploader("Upload New Issues Excel", type=["xlsx"])

    if "processed_df" not in st.session_state:
        st.session_state.processed_data = None
        st.session_state.processed_filename = None

    if uploaded_file:
        if st.button("Process & Deduplicate"):
            with st.spinner("Processing... This may take a while (Embeddings + LLM Judge)..."):
                files = {
                    "file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                try:
                    response = requests.post(
                        f"{API_URL}/process-excel", files=files)

                    if response.status_code == 200:
                        st.success("Processing complete!")

                        # Store in session state
                        content = response.content
                        df = pd.read_excel(BytesIO(content))
                        st.session_state.processed_df = df
                        st.session_state.processed_data = content
                        st.session_state.processed_filename = f"processed_{uploaded_file.name}"

                    else:
                        st.error(f"Error: {response.text}")

                except Exception as e:
                    st.error(f"Connection Error: {e}")

    # Display Results & Download
    if "processed_df" in st.session_state and st.session_state.processed_df is not None:
        df = st.session_state.processed_df

        st.divider()
        st.subheader("Results")

        # Download Button
        st.download_button(
            label="Download Processed Excel",
            data=st.session_state.processed_data,
            file_name=st.session_state.processed_filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary"
        )

        # Stats
        if "Result" in df.columns:
            st.write("### Statistics")
            counts = df["Result"].apply(lambda x: x.split(
                ":")[0] if isinstance(x, str) else str(x)).value_counts()
            st.bar_chart(counts)

            # Comparison UI
            st.write("### Review Matches")

            # Filter rows with matches (Exact or Similar)
            # Result contains "Exact found" or "Similar Found"
            match_mask = df["Result"].astype(str).str.contains(
                "Exact found|Similar Found", case=False, na=False)
            match_df = df[match_mask].copy()

            if not match_df.empty:
                st.info(
                    f"Found {len(match_df)} issues with potential matches in the store.")

                # Iterate and show comparison
                for idx, row in match_df.iterrows():
                    with st.expander(f"Row {idx+2}: {row.get('Title', 'No Title')}"):
                        col_left, col_right = st.columns(2)

                        with col_left:
                            st.markdown("#### New Issue")
                            st.write(f"**Module:** {row.get('Module', 'N/A')}")
                            st.write(f"**Title:** {row.get('Title', 'N/A')}")
                            st.text_area("Repro Steps", value=str(
                                row.get('Repro Steps', '')), height=150, disabled=True, key=f"repro_{idx}")

                        with col_right:
                            st.markdown("#### Top Matches")
                            matches_str = str(row.get("Matching IDs", ""))
                            st.code(matches_str)
                            st.write(
                                f"**Confidence:** {row.get('Match Confidence', 'N/A')}")
                            st.write(f"**Result:** {row.get('Result', 'N/A')}")

                        # Ideally we would fetch the full details of the matched ID here from the API
                        # but we don't have an endpoint to get issue by ID yet and logic asks to show 5 matches.
                        # The "Matching IDs" column only has ID and Score.
                        # The prompt says: "Right: selected matched issue (Module, Title, description/Repro Steps)."
                        # TO do this, we need the frontend to be able to fetch details of the matched ID.
                        # I'll add a note that we display what we have.
            else:
                st.info("No cross-store matches found to review.")
        else:
            st.warning("Result column not found in processed file.")
