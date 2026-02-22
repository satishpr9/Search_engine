import abc
from typing import List, Dict, Any

class VectorDB(abc.ABC):
    @abc.abstractmethod
    async def initialize(self, max_retries: int = 3):
        pass

    @abc.abstractmethod
    async def upsert(self, ids: List[str], vectors: List[List[float]], payloads: List[Dict[str, Any]]):
        """Insert or update vectors and their metadata payloads."""
        pass

    @abc.abstractmethod
    async def search(self, vector: List[float], top_k: int = 10, filter_query: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Search for similar vectors."""
        pass

class ChromaVectorDB(VectorDB):
    """
    ChromaDB implementation of the Vector DB.
    Requires `chromadb` to be installed.
    """
    def __init__(self, collection_name: str = "web_search", path: str = "chroma_data"):
        self.collection_name = collection_name
        self.path = path
        self.client = None
        self.collection = None

    async def initialize(self, max_retries: int = 3):
        # ChromaDB runs synchronously locally but we use it in async contexts
        import chromadb
        self.client = chromadb.PersistentClient(path=self.path)
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        print(f"Initialized ChromaDB collection: {self.collection_name}")

    async def upsert(self, ids: List[str], vectors: List[List[float]], payloads: List[Dict[str, Any]]):
        if not self.collection:
            raise ValueError("Vector DB not initialized. Call initialize() first.")
            
        # Ensure metadata values are strings, ints, floats, or bools format Chroma accepts
        cleaned_payloads = []
        for payload in payloads:
            clean_payload = {}
            for k, v in payload.items():
                if v is None:
                    continue
                if isinstance(v, (str, int, float, bool)):
                    clean_payload[k] = v
                else:
                    clean_payload[k] = str(v)
            cleaned_payloads.append(clean_payload)
            
        self.collection.upsert(
            embeddings=vectors,
            ids=ids,
            metadatas=cleaned_payloads
        )

    async def search(self, vector: List[float], top_k: int = 10, filter_query: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        if not self.collection:
            raise ValueError("Vector DB not initialized. Call initialize() first.")
        
        results = self.collection.query(
            query_embeddings=[vector],
            n_results=top_k,
            where=filter_query
        )
        
        # Format the output to be a list of dicts
        formatted_results = []
        if not results['ids'] or not results['ids'][0]:
            return []
            
        for i in range(len(results['ids'][0])):
            formatted_results.append({
                "id": results['ids'][0][i],
                "score": 1.0 - results['distances'][0][i] if 'distances' in results and results['distances'] else 0.0,
                "metadata": results['metadatas'][0][i] if 'metadatas' in results and results['metadatas'] else {}
            })
            
        return formatted_results
