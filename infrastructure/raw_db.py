import abc
import json
from typing import Optional, Dict, Any, List
import aiosqlite

class RawDB(abc.ABC):
    @abc.abstractmethod
    async def initialize(self):
        """Initialize the DB schema/connection"""
        pass

    @abc.abstractmethod
    async def save_html(self, url: str, html: str, headers: Dict[str, Any]) -> bool:
        """Save raw HTML and metadata. Return true if successful."""
        pass
        
    @abc.abstractmethod
    async def save_image(self, url: str, page_url: str, description: str) -> bool:
        """Save image metadata and association."""
        pass

    @abc.abstractmethod
    async def get_images(self, page_url: str) -> List[Dict[str, Any]]:
        """Retrieve images associated with a page."""
        pass

class SQLiteRawDB(RawDB):
    """
    SQLite implementation of the RawDB for storing crawled HTML pages.
    """
    def __init__(self, db_path: str = "crawler_data.db"):
        self.db_path = db_path
        
    async def initialize(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS raw_pages (
                    url TEXT PRIMARY KEY,
                    html TEXT NOT NULL,
                    headers TEXT,
                    crawled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS images (
                    url TEXT PRIMARY KEY,
                    page_url TEXT,
                    description TEXT,
                    crawled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.commit()

    async def save_html(self, url: str, html: str, headers: Dict[str, Any]) -> bool:
        try:
            headers_json = json.dumps(headers)
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO raw_pages (url, html, headers) 
                    VALUES (?, ?, ?)
                    ON CONFLICT(url) DO UPDATE SET 
                        html=excluded.html, 
                        headers=excluded.headers,
                        crawled_at=CURRENT_TIMESTAMP
                """, (url, html, headers_json))
                await db.commit()
            return True
        except Exception as e:
            print(f"Error saving HTML for {url}: {e}")
            return False

    async def get_html(self, url: str) -> Optional[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM raw_pages WHERE url = ?", (url,))
            row = await cursor.fetchone()
            if row:
                return {
                    "url": row["url"],
                    "html": row["html"],
                    "headers": json.loads(row["headers"]) if row["headers"] else {},
                    "crawled_at": row["crawled_at"]
                }
            return None
    async def save_image(self, url: str, page_url: str, description: str) -> bool:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO images (url, page_url, description) 
                    VALUES (?, ?, ?)
                    ON CONFLICT(url) DO UPDATE SET 
                        page_url=excluded.page_url,
                        description=excluded.description,
                        crawled_at=CURRENT_TIMESTAMP
                """, (url, page_url, description))
                await db.commit()
            return True
        except Exception as e:
            print(f"Error saving image {url}: {e}")
            return False

    async def get_images(self, page_url: str) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM images WHERE page_url = ?", (page_url,))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
