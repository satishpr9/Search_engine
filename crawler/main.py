import asyncio
from urllib.parse import urlparse
from .frontier import URLFrontier
from .fetcher import Fetcher
from .parser import parse_html, simhash
from .storage import StorageHelper

class CrawlerManager:
    def __init__(self, seed_urls, db_path="crawler_data.db", concurrency=5):
        self.seed_urls = seed_urls
        self.db_path = db_path
        self.concurrency = concurrency
        
        self.frontier = URLFrontier(db_path)
        self.fetcher = Fetcher()
        self.storage = StorageHelper(db_path)
        
    async def initialize(self):
        # We only need to initialize the db connections once
        if not hasattr(self, '_initialized'):
            await self.frontier.initialize()
            await self.fetcher.initialize()
            self._initialized = True
        
        for url in self.seed_urls:
            await self.frontier.add_url(url, priority=0)
            
    async def run(self):
        await self.initialize()
        
        workers = [
            asyncio.create_task(self.worker(i))
            for i in range(self.concurrency)
        ]
        
        try:
            # We run until the queue is exhausted,
            await self.frontier.queue.join()
        except asyncio.CancelledError:
            pass
        finally:
            for w in workers:
                w.cancel()
            
            # Since this is an MVP designed for short bursts or background firing,
            # we close the fetcher here. A strict daemon design would leave this open forever.
            await self.fetcher.close()

    async def crawl_single(self, url):
        """A lightweight method to trigger a targeted single-url descent, useful for the API."""
        try:
            print(f"--- Starting background crawl for: {url} ---")
            await self.initialize()
            added = await self.frontier.add_url(url, priority=0)
            print(f"URL added to frontier: {added}")
            
            # Start a temporary worker pool that dies when the queue empties
            workers = [asyncio.create_task(self.worker(i)) for i in range(2)]
            try:
                await self.frontier.queue.join()
            finally:
                for w in workers:
                    w.cancel()
                await self.fetcher.close()
                # Un-set initialized so the next request re-opens HTTP sessions
                if hasattr(self, '_initialized'):
                    delattr(self, '_initialized')
            print(f"--- Finished background crawl for: {url} ---")
        except Exception as e:
            import traceback
            print(f"CRITICAL ERROR in crawl_single: {e}")
            traceback.print_exc()

    async def worker(self, worker_id):
        while True:
            try:
                # 1. Get next URL
                priority, url = await self.frontier.get_url()
            except asyncio.CancelledError:
                break
                
            try:
                print(f"[Worker {worker_id}] Fetching: {url}")
                
                url_hash = self.frontier.get_url_hash(url)
                domain = urlparse(url).netloc
                
                # 2. Fetch the page (handles robots.txt & politeness internally)
                html, status, headers, fetch_time_ms = await self.fetcher.fetch(url)
                print(f"[Worker {worker_id}] Fetched {url} - Status: {status} - Content: {'Yes' if html else 'No'}", flush=True)
                
                # Always log the attempt
                response_size = len(html.encode('utf-8')) if html else 0
                await self.storage.save_log(url_hash, fetch_time_ms, status, response_size)
                
                if html and status == 200:
                    # 3. Parse & Extract
                    title, text, canonical_url, links = parse_html(html, url)
                    content_hash = simhash(text)
                    
                    # 4. Content Deduplication Detection
                    is_duplicate = await self.storage.check_content_duplicate(content_hash)
                    if is_duplicate:
                        print(f"  -> Duplicate content detected (Near Duplicate). Skipping indexing.")
                    else:
                        # 5. Save Page Metadata
                        success = await self.storage.save_page(
                            url_hash=url_hash,
                            url=url,
                            domain=domain,
                            title=title,
                            canonical_url=canonical_url,
                            content_hash=content_hash,
                            language="en"
                        )
                        
                        if success:
                            # 6. Index Full Text for Search
                            await self.storage.index_document(url_hash, url, title, text)
                            print(f"  -> Indexed: {title}")
                            
                            # 7. Add discovered links to frontier 
                            # (Lower priority deeper in the crawl)
                            link_hashes = []
                            for link in links:
                                if await self.frontier.add_url(link, priority=priority + 1):
                                    link_hashes.append(
                                        self.frontier.get_url_hash(self.frontier.normalize_url(link))
                                    )
                            
                            # 8. Save Graph Edges (source -> target links)
                            await self.storage.save_links(url_hash, link_hashes)
                            
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[Worker {worker_id}] Error processing {url}: {e}")
            finally:
                self.frontier.mark_done()

    @classmethod
    def get_manager(cls, db_path="crawler_data.db"):
        """Returns a singleton CrawlerManager for use in long-running processes like APIs."""
        if not hasattr(cls, '_instance'):
            cls._instance = cls([], db_path=db_path, concurrency=2)
        return cls._instance

if __name__ == "__main__":
    seeds = [
        "https://www.youtube.com/",
        "https://www.google.com/",
        "https://www.cricbuzz.com/robots.txt"
    ]
    
    crawler = CrawlerManager(seeds, concurrency=5)
    
    print("Starting Web Crawler... Press Ctrl+C to gracefully stop.")
    try:
        asyncio.run(crawler.run())
    except KeyboardInterrupt:
        print("\nStopping Crawler...")
