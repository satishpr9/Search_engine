import aiosqlite
import asyncio
from datetime import datetime
from whoosh.index import open_dir

DB_PATH = "crawler_data.db"
INDEX_DIR = "whoosh_index"

class StorageHelper:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        
    async def save_page(self, url_hash, url, domain, title, canonical_url, content_hash, language=None):
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """
                    INSERT INTO pages (url_hash, url, domain, title, canonical_url, content_hash, language, last_crawled_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(url_hash) DO UPDATE SET 
                        title=excluded.title, 
                        content_hash=excluded.content_hash, 
                        last_crawled_at=CURRENT_TIMESTAMP
                    """,
                    (url_hash, url, domain, title, canonical_url, content_hash, language)
                )
                await db.commit()
                return True
        except Exception as e:
            print(f"Error saving page {url}: {e}")
            return False

    async def check_content_duplicate(self, content_hash):
        """Check if a SimHash already exists to prevent duplicate indexing."""
        if content_hash == "0000000000000000":
            return False 
            
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("SELECT 1 FROM pages WHERE content_hash = ? LIMIT 1", (content_hash,)) as cursor:
                    result = await cursor.fetchone()
                    return result is not None
        except Exception as e:
            print(f"Error checking duplicate for {content_hash}: {e}", flush=True)
            return False

    async def save_log(self, url_hash, fetch_time_ms, http_status, response_size_bytes):
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """
                    INSERT INTO crawl_logs (url_hash, fetch_time_ms, http_status, response_size_bytes)
                    VALUES (?, ?, ?, ?)
                    """,
                    (url_hash, fetch_time_ms, http_status, response_size_bytes)
                )
                await db.commit()
        except Exception as e:
            print(f"Error saving log for {url_hash}: {e}", flush=True)

    async def save_links(self, source_url_hash, target_url_hashes):
        if not target_url_hashes:
            return
            
        try:
            async with aiosqlite.connect(self.db_path) as db:
                links_data = [(source_url_hash, target_hash, "") for target_hash in set(target_url_hashes)]
                await db.executemany(
                    """
                    INSERT OR IGNORE INTO discovered_links (source_url_hash, target_url_hash, anchor_text)
                    VALUES (?, ?, ?)
                    """,
                    links_data
                )
                await db.commit()
        except Exception as e:
            print(f"Error saving links for {source_url_hash}: {e}", flush=True)

    def _index_document_sync(self, url_hash, url, title, text):
        """Synchronous whoosh update."""
        try:
            ix = open_dir(INDEX_DIR)
            writer = ix.writer()
            writer.update_document(
                url_hash=url_hash,
                url=url,
                title=title,
                content=text,
                crawled_at=datetime.utcnow()
            )
            writer.commit()
        except Exception as e:
            print(f"Index error for {url}: {e}")

    async def index_document(self, url_hash, url, title, text):
        """Add a document to Whoosh without blocking the asyncio event loop."""
        await asyncio.to_thread(self._index_document_sync, url_hash, url, title, text)
