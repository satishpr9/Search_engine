import asyncio
import hashlib
from urllib.parse import urlparse, urljoin
from typing import Dict, Any

from agents.base_agent import BaseAgent
from infrastructure.message_queue import MessageQueue

class FrontierAgent(BaseAgent):
    """
    Manages the URL boundary. Listens for newly discovered links.
    Filters out duplicates or off-domain links.
    Pushes valid, unseen links back into the crawl_targets queue.
    """
    def __init__(self, mq: MessageQueue, allowed_domains: list = None):
        super().__init__(mq, "FrontierAgent")
        self.seen_urls = set()
        self.allowed_domains = allowed_domains or []

    def get_listen_topic(self) -> str:
        return "extracted_links_queue"
        
    def normalize_url(self, url: str) -> str:
        """Standardize URL to prevent duplicate crawls of the same page."""
        try:
            parsed = urlparse(url)
            netloc = parsed.netloc.lower()
            if netloc.startswith("www."):
                netloc = netloc[4:]
                
            normalized = f"{parsed.scheme}://{netloc}{parsed.path}"
            if parsed.query:
                query = "&".join(sorted(parsed.query.split("&")))
                normalized = f"{normalized}?{query}"
            return normalized
        except Exception:
            return url

    def is_allowed(self, url: str) -> bool:
        """Check if URL belongs to the target domain."""
        if not url.startswith(("http://", "https://")):
            return False
            
        if not self.allowed_domains:
            return True # Allow all if no domains specified
            
        try:
            domain = urlparse(url).netloc.lower()
            if domain.startswith("www."):
                domain = domain[4:]
                
            for allowed in self.allowed_domains:
                if domain == allowed or domain.endswith("." + allowed):
                    return True
            return False
        except Exception:
            return False

    async def process_message(self, message: Dict[str, Any]):
        base_url = message.get("base_url")
        links = message.get("links", [])
        
        added_count = 0
        for link in links:
            # Resolve relative links
            absolute_url = urljoin(base_url, link)
            
            # Filter by domain
            if not self.is_allowed(absolute_url):
                continue
                
            # Normalize and Deduplicate
            normalized = self.normalize_url(absolute_url)
            url_hash = hashlib.sha256(normalized.encode('utf-8')).hexdigest()
            
            if url_hash not in self.seen_urls:
                self.seen_urls.add(url_hash)
                
                # Push back into the crawler queue
                await self.mq.publish("crawl_targets", {"url": normalized})
                added_count += 1
                
        if added_count > 0:
            self.logger.info(f"Added {added_count} new distinct URLs from {base_url} to crawl queue.")
