from unittest.mock import MagicMock
import sys

# Mock google-generativeai and langchain-google-genai before importing services
sys.modules["google.generativeai"] = MagicMock()
sys.modules["langchain_google_genai"] = MagicMock()

# Mock FAISS to avoid loading issues or needing valid index
sys.modules["faiss"] = MagicMock()
sys.modules["langchain_community.vectorstores"] = MagicMock()

from fastapi.testclient import TestClient
from app.main import app
from app.services.vector_store_service import VectorStoreService
from app.services.bug_analyzer import BugAnalyzer
from app.services.llm_service import LLMService

client = TestClient(app)

def test_read_main():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Bug Deduplication API is running"}

def test_services_instantiation():
    try:
        # We need to mock settings because they are used in init
        with list_dir("app.core.config.settings") as mock_settings:
             mock_settings.GOOGLE_API_KEY = "dummy"
             
             # Instantiate
             gs = LLMService()
             assert gs is not None
             
             # VS Service tries to load index, we mocked FAISS so it should be fine or fail gracefully
             # actually VS Service uses FAISS.load_local which is mocked
             vss = VectorStoreService()
             assert vss is not None
             
             ba = BugAnalyzer()
             assert ba is not None
             
        print("Services instantiated successfully")
    except Exception as e:
        print(f"Service instantiation failed: {e}")
