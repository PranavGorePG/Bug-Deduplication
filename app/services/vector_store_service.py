import os
import json
import shutil
from datetime import datetime, timezone
from typing import List, Dict, Optional
from langchain_community.vectorstores import FAISS
from langchain_community.docstore.in_memory import InMemoryDocstore
from langchain_core.documents import Document
import faiss
from app.core.config import settings
from app.core.constants import FAISS_INDEX_PATH, VECTOR_STORE_STATUS_PATH, VECTOR_STORE_UPLOADS_PATH
from app.services.llm_service import LLMService
from app.models.schemas import Issue, VectorStoreStatus, CandidateMatch, UploadEvent


class VectorStoreService:
    def __init__(self):
        self.llm_service = LLMService()
        self.embeddings = self.llm_service.get_embeddings()
        self.vector_store = None
        self.load_or_init_index()

    # def load_or_init_index(self):
    #     if os.path.exists(FAISS_INDEX_PATH) and os.path.exists(os.path.join(FAISS_INDEX_PATH, "index.faiss")):
    #         try:
    #             self.vector_store = FAISS.load_local(FAISS_INDEX_PATH, self.embeddings, allow_dangerous_deserialization=True)
    #         except Exception as e:
    #             print(f"Error loading FAISS index: {e}. Recreating empty index.")
    #             self._create_empty_index()
    #     else:
    #         self._create_empty_index()

    # def _create_empty_index(self):
    #     # dimension 768 for text-embedding-001
    #     index = faiss.IndexFlatL2(768)
    #     self.vector_store = FAISS(
    #         embedding_function=self.embeddings,
    #         index=index,
    #         docstore=InMemoryDocstore(),
    #         index_to_docstore_id={}
    #     )
    def load_or_init_index(self):
        if os.path.exists(FAISS_INDEX_PATH) and os.path.exists(os.path.join(FAISS_INDEX_PATH, "index.faiss")):
            try:
                self.vector_store = FAISS.load_local(
                    FAISS_INDEX_PATH,
                    embeddings=self.embeddings,  # ✅ Keep "embeddings" for load_local
                    allow_dangerous_deserialization=True
                )
                # print(
                #     f"✅ Loaded FAISS with dim {self.embeddings.embed_query('test')[:5]}...")
            except Exception as e:
                print(f"Error loading: {e}. Creating new.")
                self._create_empty_index()
        else:
            self._create_empty_index()

    def _create_empty_index(self):
        # Dynamic dimension ✅
        test_embedding = self.embeddings.embed_query("test")
        d = len(test_embedding)
        print(f"✅ Embedding dim: {d}")

        index = faiss.IndexFlatL2(d)
        self.vector_store = FAISS(
            embedding_function=self.embeddings,  # ✅ "embedding_function" not "embeddings"
            index=index,
            docstore=InMemoryDocstore({}),       # ✅ Empty dict
            index_to_docstore_id={}
        )

    def append_issues(self, issues: List[Issue]) -> int:
        # Load existing IDs to avoid exact duplicates
        # Ideally this should be more efficient but for now we trust the vector store logic or just add all
        # The prompt says: "Do not insert duplicates by ID: Maintain or retrieve a mapping of existing IDs"

        # We can reconstruct existing IDs from the docstore

        existing_ids = set()

        if self.vector_store.docstore._dict:
            for doc in self.vector_store.docstore._dict.values():
                if 'id' in doc.metadata:
                    existing_ids.add(str(doc.metadata['id']))

        texts = []
        metadatas = []
        added_count = 0

        for issue in issues:
            issue_id = str(issue.id)
            if issue_id in existing_ids:
                continue

            text = f"Module: {issue.module or ''}\nTitle: {issue.title}\nSteps: {issue.repro_steps or ''}"

            metadata = {
                'id': issue_id,
                'title': issue.title,
                'module': issue.module,
                'work_item_type': getattr(issue, 'work_item_type', None),
                'repro_steps': issue.repro_steps
            }
            texts.append(text)
            metadatas.append(metadata)
            added_count += 1

        # print("texts******************************", texts)
        # print("metadatas-----------------------------------------------", metadatas)

        if texts:
            print(f"Adding {len(texts)} new docs")
            # ✅ SAFER: add_texts handles embedding + FAISS internally
            self.vector_store.add_texts(
                texts=texts,
                metadatas=metadatas
            )
            self.vector_store.save_local(FAISS_INDEX_PATH)
            print("✅ Saved!")
        return added_count

    def search(self, query_text: str, top_k: int = 5) -> List[CandidateMatch]:
        if not self.vector_store:
            return []

        results = self.vector_store.similarity_search_with_relevance_scores(
            query_text, k=top_k)

        candidates = []
        # print("Search results:", results)
        for doc, score in results:
            # Extract repro_steps from document content (format: "Module:...\nTitle:...\nSteps:...")
            # repro_steps = ""
            # content_lines = doc.page_content.split('\n')
            # for line in content_lines:
            #     if line.startswith("Steps:"):
            #         repro_steps = line[6:].strip()  # Remove "Steps:" prefix
            #         break
            # print("doc.metadata", doc.metadata.get('repro_steps', 'N/A'))

            candidate = CandidateMatch(
                id=str(doc.metadata.get('id', 'unknown')),
                title=doc.metadata.get('title', ''),
                module=doc.metadata.get('module'),
                repro_steps=doc.metadata.get('repro_steps', ''),
                # repro_steps=repro_steps,  # Add repro_steps
                score_pct=score * 100.0
            )
            candidates.append(candidate)

        return candidates

    # def search(self, query_text: str, top_k: int = 5) -> List[CandidateMatch]:
    #     if not self.vector_store:
    #         return []

    #     # FAISS similarity_search_with_score returns L2 distance by default for IndexFlatL2
    #     # But LangChain's current FAISS implementation with default normalization usually returns cosine distance or similar if normalized
    #     # Wait, text-embedding-001 is usually normalized?
    #     # Actually LangChain FAISS wrapper usually does L2 distance search.
    #     # However, for simplicity and since we need a score_pct, we can use similarity_search_with_relevance_scores
    #     # which usually attempts to return 0-1 score.
    #     # For FAISS L2, lower is better. relevance score = 1 / (1 + distance).

    #     results = self.vector_store.similarity_search_with_relevance_scores(
    #         query_text, k=top_k)

    #     candidates = []
    #     for doc, score in results:
    #         # score is 0..1
    #         score_pct = score * 100.0
    #         candidate = CandidateMatch(
    #             id=str(doc.metadata.get('id', 'unknown')),
    #             title=doc.metadata.get('title', ''),
    #             module=doc.metadata.get('module'),
    #             score_pct=score_pct
    #         )
    #         candidates.append(candidate)

    #     return candidates

    def get_status(self) -> VectorStoreStatus:
        if not os.path.exists(VECTOR_STORE_STATUS_PATH):
            return VectorStoreStatus(
                index_built=False,
                total_issues=0,
                last_updated_utc="Never",
                upload_events=0
            )
        try:
            with open(VECTOR_STORE_STATUS_PATH, 'r') as f:
                data = json.load(f)
                return VectorStoreStatus(**data)
        except:
            return VectorStoreStatus(
                index_built=False,
                total_issues=0,
                last_updated_utc="Error",
                upload_events=0
            )

    def record_upload(self, file_name: str, issues_added: int):
        now_utc = datetime.now(timezone.utc).isoformat()

        # Update status
        status = self.get_status()
        status.total_issues += issues_added
        status.last_updated_utc = now_utc
        status.upload_events += 1
        status.index_built = True

        with open(VECTOR_STORE_STATUS_PATH, 'w') as f:
            json.dump(status.model_dump(), f, indent=2)

        # Update uploads history
        upload_event = UploadEvent(
            timestamp_utc=now_utc, file_name=file_name, issues_added=issues_added)

        history = []
        if os.path.exists(VECTOR_STORE_UPLOADS_PATH):
            try:
                with open(VECTOR_STORE_UPLOADS_PATH, 'r') as f:
                    history = json.load(f)
            except:
                pass

        history.append(upload_event.model_dump())
        with open(VECTOR_STORE_UPLOADS_PATH, 'w') as f:
            json.dump(history, f, indent=2)

    def reset_store(self):
        if os.path.exists(FAISS_INDEX_PATH):
            shutil.rmtree(FAISS_INDEX_PATH)
        if os.path.exists(VECTOR_STORE_STATUS_PATH):
            os.remove(VECTOR_STORE_STATUS_PATH)
        if os.path.exists(VECTOR_STORE_UPLOADS_PATH):
            os.remove(VECTOR_STORE_UPLOADS_PATH)

        self._create_empty_index()
