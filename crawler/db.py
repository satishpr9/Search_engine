import asyncio
import sqlite3
import os
from whoosh.index import create_in, exists_in, open_dir
from whoosh.fields import Schema, TEXT, ID, DATETIME
from whoosh.analysis import StemmingAnalyzer

import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "crawler_data.db")
INDEX_DIR = os.path.join(BASE_DIR, "whoosh_index")

# SQLite Table Schemas
CREATE_PAGES_TABLE = """
CREATE TABLE IF NOT EXISTS pages (
    url_hash TEXT PRIMARY KEY,
    url TEXT NOT NULL,
    domain TEXT NOT NULL,
    title TEXT,
    canonical_url TEXT,
    content_hash TEXT,
    language TEXT,
    first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_crawled_at TIMESTAMP,
    next_crawl_at TIMESTAMP
);
"""

CREATE_LOGS_TABLE = """
CREATE TABLE IF NOT EXISTS crawl_logs (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    url_hash TEXT,
    fetch_time_ms INTEGER,
    http_status INTEGER,
    response_size_bytes INTEGER,
    crawled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(url_hash) REFERENCES pages(url_hash)
);
"""

CREATE_LINKS_TABLE = """
CREATE TABLE IF NOT EXISTS discovered_links (
    source_url_hash TEXT,
    target_url_hash TEXT,
    anchor_text TEXT,
    discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (source_url_hash, target_url_hash),
    FOREIGN KEY(source_url_hash) REFERENCES pages(url_hash)
);
"""

CREATE_ERRORS_TABLE = """
CREATE TABLE IF NOT EXISTS crawl_errors (
    error_id INTEGER PRIMARY KEY AUTOINCREMENT,
    url_hash TEXT,
    error_type TEXT,
    error_message TEXT,
    occurred_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


async def init_sqlite_db():
    print("Initializing SQLite database...")
    db = sqlite3.connect(DB_PATH)
    try:
        db.execute(CREATE_PAGES_TABLE)
        db.execute(CREATE_LOGS_TABLE)
        db.execute(CREATE_LINKS_TABLE)
        db.execute(CREATE_ERRORS_TABLE)
        
        # Create useful indexes for quick querying
        db.execute("CREATE INDEX IF NOT EXISTS idx_pages_domain ON pages(domain);")
        db.execute("CREATE INDEX IF NOT EXISTS idx_pages_next_crawl ON pages(next_crawl_at);")
        
        db.commit()
    finally:
        db.close()
    print("SQLite database initialized successfully.")


def init_whoosh_index():
    print("Initializing Whoosh search index...")
    if not os.path.exists(INDEX_DIR):
        os.mkdir(INDEX_DIR)
        
    schema = Schema(
        url_hash=ID(stored=True, unique=True),
        url=ID(stored=True),
        title=TEXT(stored=True, analyzer=StemmingAnalyzer()),
        content=TEXT(stored=True, analyzer=StemmingAnalyzer()), # Store content for snippets
        thumbnail_url=ID(stored=True),
        page_type=ID(stored=True),
        crawled_at=DATETIME(stored=True)
    )
    
    if not exists_in(INDEX_DIR):
        create_in(INDEX_DIR, schema)
        print("Created new Whoosh index.")
    else:
        print("Whoosh index already exists.")


async def init_db():
    await init_sqlite_db()
    init_whoosh_index()


if __name__ == "__main__":
    asyncio.run(init_db())
