import asyncio
import sys
import os

from infrastructure.message_queue import MemoryMessageQueue
from infrastructure.raw_db import SQLiteRawDB
from infrastructure.vector_db import ChromaVectorDB

from agents.crawl_agent import CrawlAgent
from agents.clean_agent import CleanAgent
from agents.chunk_agent import ChunkAgent
from agents.index_agent import IndexAgent
from agents.retrieval_agent import RetrievalAgent
from agents.answer_agent import AnswerAgent

async def main():
    print("=== Starting AI Search Engine Pipeline ===")
    
    # 1. Initialize Infrastructure
    mq = MemoryMessageQueue()
    raw_db = SQLiteRawDB("crawler_data.db")
    await raw_db.initialize()
    
    vector_db = ChromaVectorDB(collection_name="web_search_v2", path="chroma_data")
    await vector_db.initialize()
    
    # 2. Initialize Agents
    crawl_agent = CrawlAgent(mq, raw_db)
    clean_agent = CleanAgent(mq)
    chunk_agent = ChunkAgent(mq)
    index_agent = IndexAgent(mq, vector_db)
    
    retrieval_agent = RetrievalAgent(mq, vector_db)
    answer_agent = AnswerAgent(mq, retrieval_agent)

    # Add a snooper to print data passing through the queues!
    async def snoop_queue(topic: str, message: dict):
        print(f"\n---> [SNOOP: {topic}] Passed through queue")
        for key, value in message.items():
            if isinstance(value, str) and len(value) > 150:
                print(f"       {key}: {value[:150]}... (truncated, total length {len(value)})")
            elif isinstance(value, dict):
                print(f"       {key}: {list(value.keys())} (dictionary keys)")
            else:
                print(f"       {key}: {value}")
        print("---<")

    await mq.subscribe("raw_html_queue", lambda msg: snoop_queue("raw_html_queue", msg))
    await mq.subscribe("clean_queue", lambda msg: snoop_queue("clean_queue", msg))
    await mq.subscribe("chunk_queue", lambda msg: snoop_queue("chunk_queue", msg))
    
    # 3. Start Agents (Subscribing to queues)
    await crawl_agent.start()
    await clean_agent.start()
    await chunk_agent.start()
    await index_agent.start()
    await retrieval_agent.start()
    await answer_agent.start()
    
    print("\n=== All agents started. Running end-to-end test ===\n")
    
    # 4. Submit a target guaranteed to not 403
    test_url = "https://example.com"
    print(f"Triggering crawl for: {test_url}")
    await crawl_agent.submit_target(test_url)
    
    # Give the pipeline a few seconds to process
    print("Waiting 5 seconds for ingestion pipeline to finish (Crawl -> Clean -> Chunk -> Index)...")
    await asyncio.sleep(5)
    
    # Force flush the index agent's batch
    await index_agent._flush_batch()
    
    # 5. Test Query
    query = "What is the domain mentioned?"
    print(f"\nTesting Query Answer Agent: '{query}'")
    answer, sources = await answer_agent.answer_query(query)
    
    print("\n[Final Answer]")
    print(answer)
    print("\n[Sources]")
    for src in sources:
        print(f"- {src}")
        
    print("\n=== Test Complete ===")
    
if __name__ == "__main__":
    asyncio.run(main())
