from typing import Dict, Any, List
import hashlib
from sentence_transformers import SentenceTransformer, CrossEncoder
from rank_bm25 import BM25Okapi
from agents.base_agent import BaseAgent
from infrastructure.message_queue import MessageQueue
from infrastructure.vector_db import VectorDB

class RetrievalAgent(BaseAgent):
    """
    Given a query, retrieves the most relevant semantic chunks from the Vector Database.
    Applies re-ranking and metadata filtering.
    """
    def __init__(self, mq: MessageQueue, vector_db: VectorDB):
        super().__init__(mq, "RetrievalAgent")
        self.vector_db = vector_db
        
        self.logger.info("Loading SentenceTransformer model 'all-MiniLM-L6-v2'...")
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        
        self.logger.info("Loading CrossEncoder model 'cross-encoder/ms-marco-MiniLM-L-6-v2'...")
        self.cross_encoder = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')

    def get_listen_topic(self) -> str:
        # Retrieval usually acts synchronously on user request rather than processing a queue
        # Returning None means it won't run an infinite listener loop, but can be invoked directly
        return None

    def _generate_mock_embedding(self, text: str) -> List[float]:
        # Hash-based deterministic mock embedding for search
        h = int(hashlib.md5(text.encode('utf-8')).hexdigest(), 16)
        import random
        random.seed(h)
        vec = [random.uniform(-1, 1) for _ in range(384)]
        mag = sum(x**2 for x in vec) ** 0.5
        return [x/mag for x in vec]

    def encode(self, query: str) -> List[float]:
        if self.model:
            return self.model.encode(query).tolist()
        else:
            return self._generate_mock_embedding(query)

    def deduplicate_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove exact duplicate chunks or highly overlapping chunks if necessary."""
        seen = set()
        deduped = []
        for chunk in chunks:
            text = chunk.get("metadata", {}).get("text", "")
            if text not in seen:
                seen.add(text)
                deduped.append(chunk)
        return deduped

    async def retrieve(self, query: str, filters: Dict[str, Any] = None, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Embed the query and perform a similarity search.
        """
        query_emb = self.encode(query)
        
        self.logger.info(f"Searching DB for: '{query}'")
        raw_results = await self.vector_db.search(query_emb, top_k=top_k * 2, filter_query=filters)
        
        # Simple local deduplication
        deduped = self.deduplicate_chunks(raw_results)
        
        final_results = deduped
        
        if final_results and hasattr(self, 'cross_encoder') and self.cross_encoder:
            self.logger.info(f"Re-ranking {len(final_results)} chunks using Cross-Encoder and BM25...")
            
            # 1. Semantic Score
            cross_inputs = [[query, res.get("metadata", {}).get("text", "")] for res in final_results]
            semantic_scores = self.cross_encoder.predict(cross_inputs)
            
            # 2. Hybrid Keyword Score (BM25)
            tokenized_corpus = [res.get("metadata", {}).get("text", "").lower().split(" ") for res in final_results]
            bm25 = BM25Okapi(tokenized_corpus)
            tokenized_query = query.lower().split(" ")
            bm25_scores = bm25.get_scores(tokenized_query)
            
            # Normalize and Combine (0.7 CrossEncoder + 0.3 BM25)
            def normalize(scores):
                min_s, max_s = min(scores), max(scores)
                if max_s > min_s:
                    return [(s - min_s) / (max_s - min_s) for s in scores]
                return [1.0] * len(scores)

            sem_norm = normalize(semantic_scores)
            bm25_norm = normalize(bm25_scores)
            combined_scores = [0.7 * s + 0.3 * b for s, b in zip(sem_norm, bm25_norm)]
            
            # Sort by combined score descending
            scored_results = sorted(zip(combined_scores, final_results), key=lambda x: x[0], reverse=True)
            final_results = [res for score, res in scored_results]
            
        final_results = final_results[:top_k]
        self.logger.info(f"Retrieved {len(final_results)} final chunks.")
        
        return final_results

    async def process_message(self, message: Dict[str, Any]):
        pass
