import sys
import asyncio
import logging

from infrastructure.message_queue import MemoryMessageQueue
from infrastructure.raw_db import SQLiteRawDB
from infrastructure.vector_db import ChromaVectorDB

from agents.crawl_agent import CrawlAgent
from agents.clean_agent import CleanAgent
from agents.chunk_agent import ChunkAgent
from agents.index_agent import IndexAgent
from agents.frontier_agent import FrontierAgent
from agents.image_agent import ImageAgent

async def run_spider(start_urls: list, allowed_domains: list):
    # 1. Init Infra
    mq = MemoryMessageQueue()
    raw_db = SQLiteRawDB("crawler_data.db")
    await raw_db.initialize()
    
    vector_db = ChromaVectorDB(collection_name="web_search_v2", path="chroma_data")
    await vector_db.initialize()

    # 2. Init Agents
    # We use concurrency 1 because MemoryMessageQueue is a broadcast pub/sub
    # If we had RabbitMQ, we could use multiple consumers.
    concurrency = 1
    crawl_agents = [CrawlAgent(mq, raw_db) for _ in range(concurrency)]
    # Overwrite names so logs look distinct
    for i, ca in enumerate(crawl_agents):
        ca.name = f"CrawlAgent-{i}"
        # Set the logger again so it picks up the new name
        ca.logger = logging.getLogger(ca.name)
        
    clean_agent = CleanAgent(mq)
    chunk_agent = ChunkAgent(mq)
    index_agent = IndexAgent(mq, vector_db)
    image_agent = ImageAgent(mq, raw_db)
    frontier_agent = FrontierAgent(mq, allowed_domains)

    # 3. Start Agents
    for ca in crawl_agents:
        await ca.start()
        
    await clean_agent.start()
    await chunk_agent.start()
    await index_agent.start()
    await image_agent.start()
    await frontier_agent.start()

    # 4. Fire Crawl Seeds
    print(f"\n=== Starting Crotal Bot (Pexels-Ready) ===")
    print(f"Seeds: {start_urls}")
    print(f"Allowed Domains: {allowed_domains}")
    print(f"Concurrency: {concurrency}")
    print(f"Press Ctrl+C to stop.\n")
    
    for url in start_urls:
        await frontier_agent.process_message({
            "base_url": url,
            "links": [url] 
        })
        
    # The architecture will now spin infinitely.
    # The frontier adds to the crawl queue. 
    # Crawlers fetch and pass to clean_queue.
    # Clean extracts new links and passes them back to the frontier queue.
    try:
        while True:
            await asyncio.sleep(1)
            # Flush indexes periodically
            if index_agent.current_batch:
                await index_agent._flush_batch()
    except asyncio.CancelledError:
        pass
    except KeyboardInterrupt:
        print("\n=== Stopping Crotal Bot ===")

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, 
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S"
    )
    
    # Example Target
    seeds = ["https://www.pexels.com/robots.txt"]
    domains = ["www.pexels.com"]
    
    try:
        asyncio.run(run_spider(seeds, domains))
    except KeyboardInterrupt:
        pass
