import sys
import os
import aiosqlite
import asyncio
from bs4 import BeautifulSoup
import hashlib

# Ensure imports work from the root dir
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from whoosh.index import open_dir
from crawler.db import DB_PATH, INDEX_DIR
from crawler.parser import parse_html

async def migrate_raw_pages():
    print(f"Opening index at {INDEX_DIR}")
    if not os.path.exists(INDEX_DIR):
        from crawler.db import init_whoosh_index
        init_whoosh_index()
        
    ix = open_dir(INDEX_DIR)
    writer = ix.writer()
    
    print("Reading raw pages from SQLite...")
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT url, html, crawled_at FROM raw_pages") as cursor:
            rows = await cursor.fetchall()
            
            print(f"Found {len(rows)} raw pages. Parsing and adding to Whoosh...")
            
            count = 0
            from datetime import datetime
            
            for row in rows:
                url = row['url']
                html = row['html']
                crawled_at_str = row['crawled_at']
                
                try:
                    if crawled_at_str:
                        # Handle fractional seconds if present
                        if '.' in crawled_at_str:
                            crawled_at = datetime.strptime(crawled_at_str.split('.')[0], "%Y-%m-%d %H:%M:%S")
                        else:
                            crawled_at = datetime.strptime(crawled_at_str, "%Y-%m-%d %H:%M:%S")
                    else:
                        crawled_at = datetime.utcnow()
                except (ValueError, TypeError):
                    crawled_at = datetime.utcnow()
                    
                title, text, canonical_url, links, thumbnail_url, page_type = parse_html(html, url)
                url_hash = hashlib.sha256(url.encode('utf-8')).hexdigest()
                
                writer.update_document(
                    url_hash=str(url_hash),
                    url=url,
                    title=title or url,
                    content=text or title or "",
                    thumbnail_url=thumbnail_url,
                    page_type=page_type,
                    crawled_at=crawled_at
                )
                count += 1
                
                if count % 100 == 0:
                    print(f"  Indexed {count} pages...")
                    
    print("Committing changes to Whoosh...")
    writer.commit()
    print(f"Migrated and re-indexed {count} pages successfully.")

if __name__ == "__main__":
    asyncio.run(migrate_raw_pages())
