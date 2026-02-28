import numpy as np
from typing import List, Dict, Optional
from app.services.llm_service import LLMService
from app.services.vector_store_service import VectorStoreService
from app.core.constants import SHEET_DUP_THRESHOLD, EXACT_THRESHOLD, SIMILARITY_FLOOR
from app.models.schemas import RowDecision, CandidateMatch
from langchain_google_genai import GoogleGenerativeAIEmbeddings


class BugAnalyzer:
    def __init__(self):
        self.llm_service = LLMService()
        self.vector_store_service = VectorStoreService()

    def analyze_sheet(self, rows: List[Dict], input_ids: List[str] = None, collection_name: str = None) -> List[RowDecision]:
        # rows is list of dicts with keys: Title, Repro Steps, Module, etc.

        # 1. Precompute embeddings for in-sheet dedupe
        # textual representation for embedding: Title + \n + Repro Steps
        texts_to_embed = []
        valid_indices = []  # indices of rows that have enough data to embed

        for i, row in enumerate(rows):
            title = str(row.get("Title", "")).strip()
            steps = str(row.get("Repro Steps", "")).strip()
            if not title:
                # If title is missing, we can't really embed or it's meaningless
                # We'll just skip in-sheet dedupe for this row
                continue

            text = f"{title}\n{steps}"
            texts_to_embed.append(text)
            valid_indices.append(i)

        embeddings = []

        print(f"Valid indices: {valid_indices}")

        if texts_to_embed:
            # print(f"Norm check: {norm[:2] if 'norm' in locals() else 'OK'}")
            # Batch embed
            # GoogleGenerativeAIEmbeddings.embed_documents
            embeddings = self.llm_service.embeddings.embed_documents(
                texts_to_embed)
        # print(f"✅ Embeddings shape: {len(embeddings)} texts, matrix {embedding_matrix.shape if 'embedding_matrix' in locals() else 'N/A'}")

        # Convert to numpy array for fast cosine similarity
        embedding_matrix = np.array(embeddings)
        # Normalize for cosine similarity (dot product of normalized vectors)
        norm = np.linalg.norm(embedding_matrix, axis=1, keepdims=True)
        # Avoid division by zero
        norm[norm == 0] = 1
        normalized_matrix = embedding_matrix / norm

        decisions = [None] * len(rows)

        # 2. Iterate and process
        for i in range(len(rows)):
            row = rows[i]
            row_id = input_ids[i] if input_ids else f"row_{i+1}"
            title = str(row.get("Title", "")).strip()

            if not title:
                decisions[i] = RowDecision(
                    result="Not Found", matches=[], input_id=row_id)  # Or "Skipped"
                continue

            # --- In-sheet Deduplication ---
            # Check against previous rows j < i
            is_sheet_dup = False
            best_sheet_match_idx = -1

            # Find index in normalized_matrix
            if i in valid_indices:
                curr_emb_idx = valid_indices.index(i)
                curr_emb = normalized_matrix[curr_emb_idx]

                # We only need to compare with valid_indices that are < i
                prev_valid_indices = [idx for idx in valid_indices if idx < i]

                if prev_valid_indices:
                    # Slice matrix
                    prev_emb_indices = [valid_indices.index(
                        idx) for idx in prev_valid_indices]
                    prev_embs = normalized_matrix[prev_emb_indices]

                    # Dot product
                    sims = np.dot(prev_embs, curr_emb)
                    max_sim = np.max(sims) if sims.size > 0 else 0

                    if max_sim * 100 >= SHEET_DUP_THRESHOLD:
                        is_sheet_dup = True
                        # Find which index had max_sim
                        best_match_local_idx = np.argmax(sims)
                        best_sheet_match_idx = prev_valid_indices[best_match_local_idx]

            if is_sheet_dup:
                # 1-based index for display
                dup_row_id = input_ids[best_sheet_match_idx] if input_ids and input_ids[
                    best_sheet_match_idx] else f"row_{best_sheet_match_idx + 2}"
                decisions[i] = RowDecision(
                    # +2 because 0-based index and header row
                    result=dup_row_id,
                    dedup_within_sheet=True,
                    duplicate_of_row_index=best_sheet_match_idx,
                    input_id=row_id
                )
                continue

            # --- Cross-store Deduplication ---
            query_text = f"{title}\n{str(row.get('Repro Steps', '')).strip()}"
            # print(f"Querying store for row {i}: {query_text[:50]}...")
            candidates = self.vector_store_service.search(
                query_text, top_k=5, collection_name=collection_name)
            # print(f"Found {len(candidates)} candidates, best score: {candidates[0].score_pct if candidates else 'NONE'}")

            if not candidates:
                decisions[i] = RowDecision(
                    result="Not Found", matches=[], input_id=row_id)
                continue

            best_candidate = candidates[0]

            if best_candidate.score_pct < SIMILARITY_FLOOR:
                decisions[i] = RowDecision(
                    result="Not Found", matches=candidates, input_id=row_id)
            elif best_candidate.score_pct >= EXACT_THRESHOLD:
                decisions[i] = RowDecision(
                    result=f"Exact found: {best_candidate.id}",
                    exact_match_id=best_candidate.id,
                    llm_confirmed_duplicate=True,
                    llm_best_match_id=best_candidate.id,
                    matches=candidates,
                    input_id=row_id
                )
            else:
                # LLM Judge
                query_issue = {
                    "title": title,
                    "repro_steps": str(row.get("Repro Steps", "")).strip(),
                    "module": str(row.get("Module", "")).strip()
                }

                cand_dicts = [c.model_dump() for c in candidates]

                judge_result = self.llm_service.judge_duplicate(
                    query_issue, cand_dicts)

                if judge_result["llm_confirmed_duplicate"]:
                    decisions[i] = RowDecision(
                        result="Similar Found",
                        matches=candidates,
                        llm_confirmed_duplicate=True,
                        llm_best_match_id=judge_result["llm_best_match_id"],
                        input_id=row_id
                    )
                else:
                    decisions[i] = RowDecision(
                        result="Not Found",
                        matches=candidates,
                        llm_confirmed_duplicate=False,
                        input_id=row_id
                    )

        return decisions
