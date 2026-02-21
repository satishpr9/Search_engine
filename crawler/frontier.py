import asyncio
import hashlib
from urllib.parse import urlparse
import aiosqlite

class URLFrontier:
    def __init__(self, db_path):
        self.db_path = db_path
        self.queue = None
        self.seen_urls = set() # In-memory cache for fast dedup
        
    async def initialize(self):
        """Load already seen URLs from the database to avoid re-crawling on startup."""
        if self.queue is None:
            self.queue = asyncio.PriorityQueue()
            
        async with aiosqlite.connect(self.db_path) as db:
            # Check if table exists first (in case init script wasn't run)
            try:
                async with db.execute("SELECT url_hash FROM pages") as cursor:
                    async for row in cursor:
                        self.seen_urls.add(row[0])
            except aiosqlite.OperationalError:
                pass # Table doesn't exist yet
                
    def normalize_url(self, url):
        """Standardize URL to prevent duplicate crawls of the same page."""
        parsed = urlparse(url)
        # Drop fragments, force lowercase domain, keep path
        netloc = parsed.netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:] # normalize www to bare domain
            
        normalized = f"{parsed.scheme}://{netloc}{parsed.path}"
        if parsed.query:
            # Sort query params for consistent hashing
            query = "&".join(sorted(parsed.query.split("&")))
            normalized = f"{normalized}?{query}"
        return normalized

    def get_url_hash(self, normalized_url):
        return hashlib.sha256(normalized_url.encode()).hexdigest()

    async def add_url(self, url, priority=1):
        """Add a URL to the frontier if it hasn't been seen."""
        # A priority of 0 is highest, 1 is normal, larger numbers are lower priority
        try:
            normalized = self.normalize_url(url)
            # Only HTTP/HTTPS
            if not normalized.startswith(("http://", "https://")):
                return False
                
            url_hash = self.get_url_hash(normalized)
            
            if url_hash in self.seen_urls:
                return False
                
            self.seen_urls.add(url_hash)
            await self.queue.put((priority, normalized))
            return True
        except Exception:
            # URL decoding/parsing failed
            return False
            
    async def get_url(self):
        """Get the next highest priority URL."""
        return await self.queue.get()
        
    def mark_done(self):
        self.queue.task_done()
