from langchain_google_genai import GoogleGenerativeAIEmbeddings
from app.core.config import settings
from app.core.constants import EMBEDDING_MODEL, CHAT_MODEL
from bytez import Bytez
import json

from langchain_core.embeddings import Embeddings
import time
from typing import List


class RateLimitedEmbeddings(Embeddings):
    def __init__(self, underlying_embeddings: Embeddings, delay: float = 0.7, batch_size: int = 10):
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
            google_api_key=settings.GOOGLE_API_KEY
        )
        self.embeddings = RateLimitedEmbeddings(base_embeddings, delay=0.7)
        self.bytez_client = Bytez(settings.BYTEZ_API_KEY)

    def get_embeddings(self):
        return self.embeddings

    def judge_duplicate(self, query_issue: dict, candidates: list[dict]) -> dict:
        candidates_formatted = "\n".join([
            f"ID: {c['id']}, Module: {c.get('module')}, Title: {c['title']}, Description: {c.get('description')}"
            for c in candidates
        ])

        prompt_content = f"""
        You are an expert bug triage assistant. Determine if the following new bug report is a duplicate of any existing bug reports.

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
        
        Return the result as a valid JSON object. Do not include any markdown formatting or code blocks.
        {{
            "llm_confirmed_duplicate": boolean,
            "llm_best_match_id": "string or null"
        }}
        """

        try:
            model = self.bytez_client.model(CHAT_MODEL)
            output = model.run([
                {
                    "role": "user",
                    "content": prompt_content
                }
            ])

            # According to user snippet, output has .output
            if hasattr(output, 'output'):
                response_text = output.output
                if isinstance(response_text, dict):
                    response_text = json.dumps(
                        response_text)  # Convert dict → string
            else:
                response_text = str(output)

            # Clean markdown (safe for strings only)
            if isinstance(response_text, str):
                if response_text.startswith("```json"):
                    response_text = response_text[7:]
                if response_text.startswith("```"):
                    response_text = response_text[3:]
                if response_text.endswith("```"):
                    response_text = response_text[:-3]

                parsed = json.loads(response_text.strip())
            else:
                parsed = response_text  # Already JSON dict

            return parsed

        except Exception as e:
            print(f"Error querying Bytez or parsing response: {e}")
            return {"llm_confirmed_duplicate": False, "llm_best_match_id": None}
