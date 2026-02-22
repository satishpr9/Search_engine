import hashlib
from typing import Dict, Any, List
from sentence_transformers import SentenceTransformer
from agents.base_agent import BaseAgent
from infrastructure.message_queue import MessageQueue
from infrastructure.vector_db import VectorDB

class IndexAgent(BaseAgent):
    """
    Embeds semantic chunks into dense vectors and upserts them into
    the Vector Database.
    """
    def __init__(self, mq: MessageQueue, vector_db: VectorDB):
        super().__init__(mq, "IndexAgent")
        self.vector_db = vector_db
        
        # Batching properties
        self.batch_size = 10
        self.current_batch = []
        
        # In a real scenario, use:
        # from sentence_transformers import SentenceTransformer
        self.logger.info("Loading SentenceTransformer model 'all-MiniLM-L6-v2'...")
        self.model = SentenceTransformer('all-MiniLM-L6-v2')

    def get_listen_topic(self) -> str:
        return "chunk_queue"

    def _generate_mock_embedding(self, text: str) -> List[float]:
        """A placeholder for an actual embedding model."""
        # Returns a normalized 384-dimensional vector based on string hash for deterministic mock
        h = int(hashlib.md5(text.encode('utf-8')).hexdigest(), 16)
        import random
        random.seed(h)
        vec = [random.uniform(-1, 1) for _ in range(384)]
        # normalize
        mag = sum(x**2 for x in vec) ** 0.5
        return [x/mag for x in vec]

    def encode(self, texts: List[str]) -> List[List[float]]:
        if self.model:
            return self.model.encode(texts).tolist()
        else:
            return [self._generate_mock_embedding(t) for t in texts]

    async def _flush_batch(self):
        if not self.current_batch:
            return
            
        self.logger.info(f"Flushing batch of {len(self.current_batch)} chunks to Vector DB...")
        
        texts = []
        ids = []
        payloads = []
        
        seen_ids = set()
        
        for doc in self.current_batch:
            # Deterministic ID to prevent duplicate chunks on re-crawls
            chunk_hash = hashlib.sha256(f"{doc['url']}_{doc['chunk_index']}".encode('utf-8')).hexdigest()
            
            if chunk_hash in seen_ids:
                continue
            seen_ids.add(chunk_hash)
            
            ids.append(chunk_hash)
            texts.append(doc["chunk_text"])
            
            payload = {**doc["chunk_metadata"]}
            payload["text"] = doc["chunk_text"]
            payloads.append(payload)
            
        if not ids:
            self.current_batch = []
            return
            
        embeddings = self.encode(texts)
        await self.vector_db.upsert(ids=ids, vectors=embeddings, payloads=payloads)
        self.current_batch = []
        self.logger.info(f"Batch upsert complete. ({len(ids)} unique chunks)")

    async def process_message(self, message: Dict[str, Any]):
        self.current_batch.append(message)
        
        if len(self.current_batch) >= self.batch_size:
            await self._flush_batch()
