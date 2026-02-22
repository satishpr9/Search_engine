import asyncio
import time
import aiohttp
import cloudscraper
from typing import Dict, Any, List
from agents.base_agent import BaseAgent
from infrastructure.message_queue import MessageQueue
from infrastructure.raw_db import RawDB

class CrawlAgent(BaseAgent):
    """
    Responsible for fetching URLs, storing raw HTML, and triggering the Clean Agent.
    """
    def __init__(self, mq: MessageQueue, raw_db: RawDB):
        super().__init__(mq, "CrawlAgent")
        self.raw_db = raw_db
        # In a real system, respect robots.txt and store crawl delays natively mapped per domain.

    def get_listen_topic(self) -> str:
        return "crawl_targets"

    def _sync_fetch_url(self, url: str) -> Dict[str, Any]:
        """Synchronous fetch using cloudscraper to bypass 403 Forbidden Cloudflare/bot protections."""
        scraper = cloudscraper.create_scraper(browser={
            'browser': 'chrome',
            'platform': 'windows',
            'desktop': True
        })
        try:
            response = scraper.get(url, timeout=15)
            # Cloudscraper auto-handles rendering/JS bypasses
            return {
                "html": response.text,
                "status": response.status_code,
                "headers": dict(response.headers)
            }
        except Exception as e:
            print(f"[CrawlAgent] Sync Error crawling {url}: {e}")
            return None

    async def fetch_url(self, url: str) -> Dict[str, Any]:
        """Async wrapper for the blocking cloudscraper."""
        return await asyncio.to_thread(self._sync_fetch_url, url)

    async def process_message(self, message: Dict[str, Any]):
        url = message.get("url")
        if not url:
            return
            
        print(f"[CrawlAgent] Crawling: {url}")
        result = await self.fetch_url(url)
        
        if result and result["status"] == 200:
            html = result["html"]
            headers = result["headers"]
            
            # Save to raw DB
            success = await self.raw_db.save_html(url, html, headers)
            
            if success:
                print(f"[CrawlAgent] Successfully saved {url}. Pushing to raw_html_queue...")
                # Push to the next microservice (Clean Agent)
                await self.mq.publish("raw_html_queue", {
                    "url": url,
                    "raw_html": html,
                    "timestamp": time.time(),
                    "headers": headers
                })
        else:
            status = result["status"] if result else "Failed"
            print(f"[CrawlAgent] Skipped {url} due to bad status: {status}")

    async def submit_target(self, url: str):
        """Helper to programmatically push a URL to crawl."""
        await self.mq.publish(self.get_listen_topic(), {"url": url})
