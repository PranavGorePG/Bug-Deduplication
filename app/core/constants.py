import os

# Paths
DATA_DIR = "data"
FAISS_INDEX_PATH = os.path.join(DATA_DIR, "faiss_index")
VECTOR_STORE_STATUS_PATH = os.path.join(DATA_DIR, "vector_store_status.json")
VECTOR_STORE_UPLOADS_PATH = os.path.join(DATA_DIR, "vector_store_uploads.json")

# Models
EMBEDDING_MODEL = "models/gemini-embedding-001"
CHAT_MODEL = "inference-net/Schematron-3B"

# Thresholds
SHEET_DUP_THRESHOLD = 90.0
EXACT_THRESHOLD = 85.0
SIMILARITY_FLOOR = 60.0

# Columns
REQUIRED_COLUMNS = ["ID", "Work Item Type", "Title", "Repro Steps", "Module"]
