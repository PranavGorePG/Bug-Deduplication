from langchain_google_genai import GoogleGenerativeAIEmbeddings
from app.core.config import settings
from app.core.constants import EMBEDDING_MODEL, CHAT_MODEL
from bytez import Bytez
import json

from langchain_core.embeddings import Embeddings
import time
from typing import List


class RateLimitedEmbeddings(Embeddings):
    def __init__(self, underlying_embeddings: Embeddings, delay: float = 1, batch_size: int = 10):
        self.underlying = underlying_embeddings
        self.delay = delay
        self.batch_size = batch_size

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        all_embeddings = []
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            if i > 0:
                time.sleep(self.delay)
            embeddings = self.underlying.embed_documents(batch)
            all_embeddings.extend(embeddings)
        return all_embeddings

    def embed_query(self, text: str) -> List[float]:
        time.sleep(self.delay)
        return self.underlying.embed_query(text)


class LLMService:
    def __init__(self):
        base_embeddings = GoogleGenerativeAIEmbeddings(
            model=EMBEDDING_MODEL,
            google_api_key=settings.GOOGLE_API_KEY,
            output_dimensionality=3072
        )
        self.embeddings = RateLimitedEmbeddings(base_embeddings, delay=0.7)
        self.bytez_client = Bytez(settings.BYTEZ_API_KEY)

    def get_embeddings(self):
        return self.embeddings

    def judge_duplicate(self, query_issue: dict, candidates: list[dict]) -> dict:
        candidates_formatted = "\n".join([
            f"ID: {c['id']}, Module: {c.get('module', 'N/A')}, Title: {c['title']}, Steps: {c.get('repro_steps', c.get('description', 'N/A'))}"
            for c in candidates
        ])

        prompt_content = f"""You are an expert bug triage assistant. Determine if the following new bug report is a duplicate of any existing bug reports.

    New Bug Report:
    Title: {query_issue.get("title")}
    Module: {query_issue.get("module")}
    Steps: {query_issue.get("repro_steps")}

    Existing Candidates:
    {candidates_formatted}

    Task:
    1. Analyze if the new bug report describes the SAME underlying issue as any of the candidates.
    2. Focus on semantic similarity, core failure mode, and reproduction steps.
    3. If it is a duplicate, set 'llm_confirmed_duplicate' to true and provide the 'llm_best_match_id'.
    4. If it is NOT a duplicate, set 'llm_confirmed_duplicate' to false and 'llm_best_match_id' to null.

    Return ONLY valid JSON. No other text:
    {{"llm_confirmed_duplicate": true/false, "llm_best_match_id": "ID or null"}}"""

        try:
            model = self.bytez_client.model(CHAT_MODEL)
            output = model.run([{"role": "user", "content": prompt_content}])

            # Handle Bytez chat format {'role': 'assistant', 'content': '...'}
            response_obj = getattr(output, 'output', output)

            # Extract content
            if isinstance(response_obj, dict) and 'content' in response_obj:
                response_text = str(response_obj['content']).strip()
            else:
                response_text = str(response_obj).strip()

            # Strip markdown wrappers
            for marker in ["```json", "```"]:
                if response_text.startswith(marker):
                    response_text = response_text[len(marker):].strip()
                if response_text.endswith(marker):
                    response_text = response_text[:-len(marker)].strip()

            # Parse JSON + ensure string ID
            parsed = {"llm_confirmed_duplicate": False,
                      "llm_best_match_id": None}
            try:
                parsed = json.loads(response_text)
                if parsed.get('llm_best_match_id') is not None:
                    parsed['llm_best_match_id'] = str(
                        parsed['llm_best_match_id'])
            except json.JSONDecodeError:
                pass  # Fallback already set

            return parsed

        except Exception as e:
            print(f"Bytez error: {e}")
            return {"llm_confirmed_duplicate": False, "llm_best_match_id": None}
