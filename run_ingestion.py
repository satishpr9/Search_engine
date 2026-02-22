import sys
import asyncio
import json
import uuid
import hashlib
from datetime import datetime, timezone

from infrastructure.message_queue import MemoryMessageQueue
from infrastructure.raw_db import SQLiteRawDB
from infrastructure.vector_db import ChromaVectorDB

from agents.crawl_agent import CrawlAgent
from agents.clean_agent import CleanAgent
from agents.chunk_agent import ChunkAgent
from agents.index_agent import IndexAgent

async def process_one_off_url(url: str):
    # 1. Init Infra
    mq = MemoryMessageQueue()
    raw_db = SQLiteRawDB("crawler_data.db")
    await raw_db.initialize()
    
    vector_db = ChromaVectorDB(collection_name="web_search_v2", path="chroma_data")
    await vector_db.initialize()

    # 2. Init Agents
    crawl_agent = CrawlAgent(mq, raw_db)
    clean_agent = CleanAgent(mq)
    chunk_agent = ChunkAgent(mq)
    index_agent = IndexAgent(mq, vector_db)

    # Global state capture for final JSON
    state = {
        "url": url,
        "clean_hash": None,
        "chunks_generated": 0,
        "document_id": str(uuid.uuid4())
    }

    # Queue observation hooks
    async def track_clean(msg: dict):
        state["clean_hash"] = msg.get("hash")
        
    async def track_chunk(msg: dict):
        state["chunks_generated"] += 1

    await mq.subscribe("clean_queue", track_clean)
    await mq.subscribe("chunk_queue", track_chunk)

    # 3. Start Agents
    await crawl_agent.start()
    await clean_agent.start()
    await chunk_agent.start()
    await index_agent.start()

    # 4. Fire Crawl
    await crawl_agent.submit_target(url)
    
    # Wait for the async pipeline to settle
    await asyncio.sleep(8)
    
    # Force flush embeddings
    await index_agent._flush_batch()
    
    vectors_saved = state["chunks_generated"] if state["clean_hash"] else 0
    chunks_saved = state["chunks_generated"] if state["clean_hash"] else 0
    
    # Check if duplicate (Mock logic: if no chunks were emitted, it was stopped intentionally or failed)
    status = "success" if chunks_saved > 0 else "skipped_or_failed"

    output = {
        "status": status,
        "url": url,
        "document_id": state["document_id"],
        "chunks_saved": chunks_saved,
        "vectors_saved": vectors_saved,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    print("\n--- FINAL OUTPUT ---")
    print(json.dumps(output, indent=2))

if __name__ == "__main__":
    url = sys.argv[1]
    # Reduce logging verbosity for clean output
    import logging
    logging.getLogger().setLevel(logging.WARNING)
    
    asyncio.run(process_one_off_url(url))
