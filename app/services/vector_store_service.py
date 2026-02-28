import os
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams
from langchain_qdrant import Qdrant
from langchain_core.documents import Document
from app.core.config import settings
from app.services.llm_service import LLMService
from app.models.schemas import Issue, CandidateMatch, VectorStoreStatus
from app.core.logging import logger


class VectorStoreService:
    def __init__(self):
        self.llm_service = LLMService()
        self.embeddings = self.llm_service.get_embeddings()
        self.client = QdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY,
            timeout=60
        )
        self.default_collection: Optional[str] = None

    def normalize_collection_name(self, product_name: str) -> str:
        return product_name.lower().replace(" ", "_").replace("-", "_")

    def collection_exists(self, collection_name: str) -> bool:
        """✅ FIXED: Check collections list"""
        try:
            collections = self.client.get_collections().collections
            return any(c.name == collection_name for c in collections)
        except:
            return False

    def set_collection(self, product_name: str):
        self.default_collection = self.normalize_collection_name(product_name)
        logger.info(f"Active collection: {self.default_collection}")

    def create_collection(self, product_name: str) -> str:
        collection_name = self.normalize_collection_name(product_name)

        if self.collection_exists(collection_name):
            logger.info(f"Collection exists: {collection_name}")
            return collection_name

        test_emb = self.embeddings.embed_query("test")
        self.client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=len(test_emb),
                distance=Distance.COSINE
            )
        )
        logger.info(f"✅ Created: {collection_name}")
        return collection_name

    def delete_collection(self, product_name: str):
        collection_name = self.normalize_collection_name(product_name)
        if self.collection_exists(collection_name):
            self.client.delete_collection(collection_name)
            logger.info(f"🗑️ Deleted: {collection_name}")
        else:
            logger.warning(f"Collection not found: {collection_name}")

    def get_collection_status(self, collection_name: Optional[str] = None) -> VectorStoreStatus:
        """✅ FIXED: Use collection_exists"""
        coll = collection_name or self.default_collection
        if not coll or not self.collection_exists(coll):
            return VectorStoreStatus(
                collection_name=coll or "none",
                index_built=False,
                total_issues=0,
                last_updated_utc="Never",
                upload_events=0
            )

        try:
            count = self.client.count(collection_name=coll).count
            return VectorStoreStatus(
                collection_name=coll,
                index_built=True,
                total_issues=count,
                last_updated_utc=datetime.now(timezone.utc).isoformat(),
                upload_events=1
            )
        except Exception as e:
            logger.error(f"Status error for {coll}: {e}")
            return VectorStoreStatus(
                collection_name=coll,
                index_built=False,
                total_issues=0,
                last_updated_utc="Error",
                upload_events=0
            )

    def append_issues(self, issues: List[Issue]) -> int:
        if not self.default_collection:
            raise ValueError("Call set_collection(product_name) first")

        docs = []
        added_count = 0

        for issue in issues:
            text = f"Product: {issue.product}\nTitle: {issue.title}\nModule: {issue.module or ''}\nSteps: {issue.repro_steps}"
            doc = Document(page_content=text, metadata={**issue.model_dump(),  # ✅ All fields including 'id'
                                                        "original_id": issue.id  # ✅ Explicit!
                                                        })
            docs.append(doc)
            added_count += 1

        if docs:
            vectorstore = Qdrant(
                client=self.client,
                collection_name=self.default_collection,
                embeddings=self.embeddings
            )
            vectorstore.add_documents(docs)
            logger.info(f"Added {len(docs)} to {self.default_collection}")

        return added_count

    # def search(self, query_text: str, top_k: int = 5, collection_name: str = None) -> List[CandidateMatch]:
    #     coll = collection_name or self.default_collection
    #     if not coll or not self.collection_exists(coll):
    #         return []

    #     query_vector = self.embeddings.embed_query(query_text)  # ✅ 3072 dims

    #     # ✅ NATIVE Qdrant (perfect!)
    #     response = self.client.query_points(
    #         collection_name=coll,
    #         query=query_vector,
    #         limit=top_k
    #     )

    #     candidates = []
    #     for point in response.points:
    #         meta = point.payload
    #         candidates.append(CandidateMatch(
    #             id=meta.get('original_id', meta.get('id', str(point.id))),
    #             title=meta.get('title', ''),
    #             module=meta.get('module'),
    #             repro_steps=meta.get('repro_steps', ''),
    #             score_pct=round(point.score * 100, 2)  # ✅ 0-100%
    #         ))

    #     print(f"🔍 Point ID: {point.id}, Payload keys: {list(meta.keys())}")
    #     print(
    #         f"  title: '{meta.get('title')}', repro: '{meta.get('repro_steps', '')[:50]}'")

    #     return candidates
    def search(self, query_text: str, top_k: int = 5, collection_name: str = None) -> List[CandidateMatch]:
        """
        Native Qdrant search with full metadata extraction.
        """
        coll = collection_name or self.default_collection
        if not coll or not self.collection_exists(coll):
            logger.warning(f"Empty collection: {coll}")
            return []

        logger.info(f"🔍 Searching '{coll}' for: {query_text[:100]}...")

        # Generate query embedding
        query_vector = self.embeddings.embed_query(query_text)

        # Native Qdrant query_points
        response = self.client.query_points(
            collection_name=coll,
            query=query_vector,
            limit=top_k
        )

        candidates = []
        for point in response.points:
            payload = point.payload

            # ✅ Handle BOTH LangChain nested AND flat metadata
            if isinstance(payload, dict) and 'metadata' in payload:
                # LangChain: {"page_content":..., "metadata":{...}}
                meta = payload['metadata']
            else:
                meta = payload  # Flat payload

            # ✅ Extract fields with fallbacks
            candidate = CandidateMatch(
                id=meta.get('original_id') or meta.get('id') or str(point.id),
                title=meta.get('title', '') or '',
                module=meta.get('module', None),
                repro_steps=meta.get('repro_steps', '') or '',
                score_pct=round(float(point.score) * 100, 2)
            )

            candidates.append(candidate)

            # Debug log
            logger.debug(
                f"  Match: {candidate.id} ({candidate.score_pct}%) '{candidate.title[:50]}...'")

        logger.info(f"✅ Found {len(candidates)} matches in {coll}")
        return candidates

    def get_status(self) -> VectorStoreStatus:
        """Legacy support"""
        return self.get_collection_status()

    def list_collections(self) -> List[Dict[str, Any]]:
        try:
            # uses QdrantClient.get_collections()[web:20][web:17]
            collections = self.client.get_collections().collections
            return [
                {
                    "name": c.name,
                    "vectors_count": getattr(c, "vectors_count", None),
                    "status": getattr(c, "status", None),
                }
                for c in collections
            ]
        except Exception as e:
            logger.error(f"Error listing collections: {e}")
            return []
