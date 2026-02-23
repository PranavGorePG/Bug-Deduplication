import sys
from unittest.mock import MagicMock

# Mock google-generativeai and langchain-google-genai before importing services
sys.modules["google.generativeai"] = MagicMock()
sys.modules["langchain_google_genai"] = MagicMock()

# Mock Bytez
sys.modules["bytez"] = MagicMock()

# Set dummy env vars to avoid pydantic validation error
import os
os.environ["GOOGLE_API_KEY"] = "dummy_google_key"
os.environ["BYTEZ_API_KEY"] = "dummy_bytez_key"

import json
from app.services.llm_service import LLMService
from unittest.mock import patch

def test_llm_service():
    print("Testing LLMService...")
    
    with patch("app.services.llm_service.Bytez") as MockBytez:
        # Configuration for the mock
        mock_instance = MockBytez.return_value
        mock_model = mock_instance.model.return_value
        
        # Mock response
        expected_response = {
            "llm_confirmed_duplicate": True,
            "llm_best_match_id": "12345"
        }
        mock_output = MagicMock()
        mock_output.output = json.dumps(expected_response)
        mock_model.run.return_value = mock_output
        
        # Instantiate service
        service = LLMService()
        
        # Test input
        query_issue = {
            "title": "Crash when clicking button",
            "module": "UI",
            "repro_steps": "1. Open app 2. Click button"
        }
        candidates = [
            {"id": "12345", "title": "Button crash", "module": "UI", "description": "App crashes on click"}
        ]
        
        # Run method
        result = service.judge_duplicate(query_issue, candidates)
        
        print(f"Result: {result}")
        
        # Assertions
        assert result == expected_response
        print("Verification passed!")

if __name__ == "__main__":
    test_llm_service()
