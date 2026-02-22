import hashlib
import time
from typing import Dict, Any, Tuple
from bs4 import BeautifulSoup

from agents.base_agent import BaseAgent
from infrastructure.message_queue import MessageQueue

class CleanAgent(BaseAgent):
    """
    Cleans raw HTML by removing boilerplate (ads, navbars, footers).
    Extracts the main content and metadata using DOM heuristics.
    """
    def __init__(self, mq: MessageQueue):
        super().__init__(mq, "CleanAgent")

    def get_listen_topic(self) -> str:
        return "raw_html_queue"

    def extract_main_content(self, html: str, url: str) -> Tuple[str, Dict[str, Any], list, list]:
        """
        Uses heuristics to extract the main content.
        For production, libraries like `trafilatura` are recommended.
        """
        soup = BeautifulSoup(html, "html.parser")
        
        # 1. Extract links before decomposing navigation/footers
        links = []
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href'].strip()
            if href and not href.startswith(('javascript:', 'mailto:', 'tel:')):
                links.append(href)
                
        # 2. Extract images
        images = []
        for img in soup.find_all('img'):
            # Pexels and other sites often use data-src or srcset for high-res
            img_url = img.get('data-src') or img.get('src')
            if not img_url:
                continue
                
            # Heuristic for high-res Pexels images: they often have 'photos' in URL 
            # and avoid tiny thumbnails (e.g. icons, small avatars)
            is_pexels = "pexels.com" in url
            alt = img.get('alt', '').strip()
            
            # Filter out tiny things or non-image assets
            if img_url.startswith('data:') or len(img_url) < 10:
                continue
                
            images.append({
                "url": img_url,
                "description": alt if alt else f"Image from {url}"
            })
                
        # 2. Remove script, style, ad elements
        for element in soup(["script", "style", "nav", "footer", "aside", "header"]):
            element.decompose()
            
        # 3. Extract title
        title = soup.title.string if soup.title else ""
        
        # 4. Simple heuristic: join paragraphs, fallback to body text
        paragraphs = soup.find_all('p')
        if paragraphs:
            dirty_text = "\n\n".join(p.get_text() for p in paragraphs)
        else:
            dirty_text = soup.get_text(separator="\n\n")
            
        # Normalize whitespace (simple version)
        clean_text = "\n".join([line.strip() for line in dirty_text.splitlines() if line.strip()])
        
        metadata = {
            "title": title.strip() if title else "Unknown",
            "author": "Unknown", # Requires more advanced extraction
            "publish_date": getattr(time, "time_ns", time.time)() # Mock pub date
        }
        
        return clean_text, metadata, links, images

    async def process_message(self, message: Dict[str, Any]):
        raw_html = message.get("raw_html")
        url = message.get("url")
        
        if not raw_html or not url:
            return
            
        self.logger.info(f"Cleaning HTML from: {url}")
        
        clean_text, metadata, links, images = self.extract_main_content(raw_html, url)
        
        # Deduplication check via hashing
        content_hash = hashlib.sha256(clean_text.encode('utf-8')).hexdigest()
        
        # In a real system, you would check `content_hash` against a fast KV store (Redis) 
        # to ensure you don't process exactly the same text twice.
        
        clean_doc = {
            "clean_text": clean_text,
            "metadata": metadata,
            "url": url,
            "hash": content_hash
        }
        
        self.logger.info(f"Finished cleaning {url}. Found {len(links)} links. Pushing to clean_queue and extracted_links_queue...")
        
        # Route main text down pipeline
        await self.mq.publish("clean_queue", clean_doc)
        
        # Route discovered links to Frontier
        if links:
            await self.mq.publish("extracted_links_queue", {
                "base_url": url,
                "links": links
            })
            
        # Route discovered images to ImageAgent
        if images:
            self.logger.info(f"Extracted {len(images)} images from {url}")
            for img in images:
                await self.mq.publish("image_queue", {
                    "url": img["url"],
                    "page_url": url,
                    "description": img["description"]
                })
