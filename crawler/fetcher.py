import asyncio
import aiohttp
import urllib.robotparser
from urllib.parse import urlparse
import time

USER_AGENT = "LocalCrawlerBot/1.0 (+http://localhost/bot.html)"

class Fetcher:
    def __init__(self, session_timeout=15, max_redirects=5):
        self.robot_parsers = {}
        self.last_fetch_time = {} # domain -> timestamp for crawl-delay
        self.timeout = aiohttp.ClientTimeout(total=session_timeout)
        self.max_redirects = max_redirects
        self.session = None

    async def initialize(self):
        """Initialize the shared HTTP session for connection pooling."""
        connector = aiohttp.TCPConnector(limit=100, ttl_dns_cache=300)
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=self.timeout,
            headers={"User-Agent": USER_AGENT, "Accept-Encoding": "gzip, deflate, br"}
        )

    async def close(self):
        """Gracefully close the session."""
        if self.session:
            await self.session.close()

    async def get_robot_parser(self, url):
        """Fetch and parse robots.txt for a given domain."""
        domain = urlparse(url).netloc
        if domain not in self.robot_parsers:
            rp = urllib.robotparser.RobotFileParser()
            robots_url = f"{urlparse(url).scheme}://{domain}/robots.txt"
            try:
                async with self.session.get(robots_url, timeout=5) as resp:
                    if resp.status == 200:
                        content = await resp.text()
                        rp.parse(content.splitlines())
                    else:
                        rp.allow_all = True
            except Exception:
                rp.allow_all = True # Default to allow all if robots.txt is unreachable
            self.robot_parsers[domain] = rp
        return self.robot_parsers[domain]

    async def enforce_politeness(self, url):
        """Check robots.txt and delay if necessary to respect crawl-delay."""
        domain = urlparse(url).netloc
        rp = await self.get_robot_parser(url)
        
        if not rp.can_fetch(USER_AGENT, url):
            return False

        # Use robots.txt crawl-delay if present, otherwise default to a polite 0.5s local delay
        crawl_delay = rp.crawl_delay(USER_AGENT) or 0.5 
        
        last_time = self.last_fetch_time.get(domain, 0)
        now = time.time()
        time_since_last = now - last_time
        
        if time_since_last < crawl_delay:
            await asyncio.sleep(crawl_delay - time_since_last)
            
        self.last_fetch_time[domain] = time.time()
        return True

    async def fetch(self, url):
        """Fetch the URL, returning (html_content, status_code, headers, fetch_time_ms)."""
        if not await self.enforce_politeness(url):
            return None, 403, None, 0 # Treated as forbidden by robots.txt
            
        start_time = time.perf_counter()
        try:
            async with self.session.get(url, allow_redirects=True, max_redirects=self.max_redirects) as resp:
                status = resp.status
                headers = resp.headers
                fetch_time_ms = int((time.perf_counter() - start_time) * 1000)
                
                # We only want to process HTML pages
                content_type = headers.get("Content-Type", "").lower()
                if "text/html" not in content_type:
                    return None, status, headers, fetch_time_ms
                    
                # Read content with a size limit (e.g., 5MB) to prevent OOM on huge pages
                html = await resp.text()
                return html, status, headers, fetch_time_ms
                
        except asyncio.TimeoutError:
            return None, 408, None, int((time.perf_counter() - start_time) * 1000)
        except aiohttp.ClientError:
            return None, 500, None, int((time.perf_counter() - start_time) * 1000)
        except Exception:
            return None, 500, None, int((time.perf_counter() - start_time) * 1000)
