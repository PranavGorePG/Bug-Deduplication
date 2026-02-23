# Bug Deduplication App 🐞

A production-ready web application for deduplicating bug reports using Retrieval-Augmented Generation (RAG) with LangChain, FAISS, and Google Gemini.

## Features

- **Vector Store**: Persistent FAISS index for storing existing issues.
- **In-Sheet Deduplication**: Detects duplicates within the uploaded new issues file.
- **Cross-Store Deduplication**: Detects duplicates between new issues and the existing vector store.
- **LLM Judge**: Uses Google Gemini 2.5 Flash Lite to confirm "Similar" matches with high accuracy.
- **Reporting**: Generates an Excel report with deduplication results, matching IDs, and confidence levels.

## Tech Stack

- **Backend**: FastAPI
- **Frontend**: Streamlit
- **AI/ML**: LangChain, FAISS, Google Gemini (Embeddings & Chat)
- **Data**: Pandas, OpenPyXL

## Setup

1.  **Clone the repository** (if applicable).
2.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
3.  **Environment Variables**:
    - Copy `.env.example` to `.env`:
        ```bash
        cp .env.example .env
        ```
        (On Windows: `copy .env.example .env`)
    - Edit `.env` and add your `GOOGLE_API_KEY`.

## Running the App

You need to run both the backend and frontend.

### 1. Backend (FastAPI)
Run the following command from the root directory:
```bash
uvicorn app.main:app --reload
```
The API will be available at `http://localhost:8000`.

### 2. Frontend (Streamlit)
Open a new terminal, navigate to the root directory, and run:
```bash
streamlit run streamlit_app/app.py
```
The UI will open in your browser at `http://localhost:8501`.

## Usage

1.  **Vector Store Management**:
    - Go to "Vector Store Management" in the sidebar.
    - Upload your "Already Reported Issues" CSV/Excel file.
    - Click "Append Issues" to populate the vector store.
2.  **Deduplicate New Issues**:
    - Go to "Dedup New Issues" in the sidebar.
    - Upload a new issues Excel file.
    - Click "Process & Deduplicate".
    - Download the processed Excel file with results.
    - Review matches in the "Results Preview" section.

## Directory Structure

```
app/
  main.py                # FastAPI entry point
  api/                   # API Routes
  services/              # Core business logic (Gemini, FAISS, Dedupe)
  repositories/          # Data access (CSV, Excel)
  models/                # Pydantic schemas
  core/                  # Config & Constants
streamlit_app/
  app.py                 # Streamlit Frontend
data/                    # Data storage (FAISS index, logs)
```
