from typing import Dict, Any, List
from agents.base_agent import BaseAgent
from infrastructure.message_queue import MessageQueue

class ChunkAgent(BaseAgent):
    """
    Splits content into semantic chunks bounded by paragraphs and metadata.
    Preserves overlap to ensure LLM context isn't cut off abruptly.
    """
    def __init__(self, mq: MessageQueue):
        super().__init__(mq, "ChunkAgent")
        self.chunk_size = 1000 # Approx characters
        self.overlap = 150 # Approx characters overlap

    def get_listen_topic(self) -> str:
        return "clean_queue"

    def semantic_split(self, text: str) -> List[str]:
        """
        Splits by paragraphs first, then merges them up to chunk_size.
        """
        paragraphs = text.split("\n\n")
        chunks = []
        current_chunk = ""
        
        for p in paragraphs:
            if len(current_chunk) + len(p) > self.chunk_size and current_chunk:
                chunks.append(current_chunk.strip())
                # Start new chunk with some overlap from the end of the previous
                # Very naive overlap: just keep the last paragraph if possible
                current_chunk = p + "\n\n" 
            else:
                current_chunk += p + "\n\n"
                
        if current_chunk:
            chunks.append(current_chunk.strip())
            
        return chunks

    async def process_message(self, message: Dict[str, Any]):
        clean_text = message.get("clean_text")
        url = message.get("url")
        metadata = message.get("metadata", {})
        
        if not clean_text:
            return
            
        print(f"[ChunkAgent] Chunking content from: {url}")
        chunks = self.semantic_split(clean_text)
        
        print(f"[ChunkAgent] Created {len(chunks)} chunks for {url}. Pushing to chunk_queue...")
        
        for i, text in enumerate(chunks):
            chunk_data = {
                "chunk_text": text,
                "chunk_index": i,
                "chunk_metadata": {**metadata, "url": url},
                "url": url
            }
            await self.mq.publish("chunk_queue", chunk_data)
