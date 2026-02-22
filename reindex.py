import asyncio
import sqlite3
import os
import sys

# Ensure imports work from the root dir
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from whoosh.index import open_dir

from crawler.db import DB_PATH, INDEX_DIR

def get_db_connection():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    return db

def reindex_all():
    print(f"Opening index at {INDEX_DIR}")
    if not os.path.exists(INDEX_DIR):
        print("Index directory not found!")
        return
        
    ix = open_dir(INDEX_DIR)
    writer = ix.writer()
    
    db = get_db_connection()
    cursor = db.cursor()
    
    print("Reading all pages from SQLite...")
    cursor.execute("SELECT url_hash, url, title, last_crawled_at FROM pages")
    rows = cursor.fetchall()
    
    print(f"Found {len(rows)} pages. Adding to Whoosh...")
    
    count = 0
    from datetime import datetime
    for row in rows:
        # Note: We can't recover full HTML text from SQLite since we only store a hash.
        # But we can index the URL and title at least so it's searchable.
        
        crawled_at = row['last_crawled_at']
        if isinstance(crawled_at, str):
            try:
                # Format: 2026-02-19 16:47:11
                crawled_at = datetime.strptime(crawled_at, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                crawled_at = datetime.utcnow()
                
        writer.update_document(
            url_hash=row['url_hash'],
            url=row['url'],
            title=row['title'] or "",
            content=row['title'] or "", # Fallback content
            crawled_at=crawled_at
        )
        count += 1
        
        if count % 1000 == 0:
            print(f"  Indexed {count} pages...")
            
    print("Committing changes to Whoosh...")
    writer.commit()
    print(f"Re-indexed {count} pages successfully.")

if __name__ == "__main__":
    reindex_all()
