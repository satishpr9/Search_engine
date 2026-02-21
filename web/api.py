from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional
from whoosh.index import open_dir
from whoosh.qparser import QueryParser
import os
import aiosqlite
import time

# Import the crawler logic to spawn single-url runs from the UI
import sys
# We need to add the parent directory to sys.path to easily import the crawler module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from crawler.main import CrawlerManager

app = FastAPI(title="Nexus Search API")

# Setup paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
INDEX_DIR = os.path.join(os.path.dirname(BASE_DIR), "whoosh_index")
DB_PATH = os.path.join(os.path.dirname(BASE_DIR), "crawler_data.db")

# Mount the static directory to serve index.html, style.css, script.js
# This means navigating to http://localhost:8000/ will load index.html
app.mount("/app", StaticFiles(directory=STATIC_DIR, html=True), name="static")


class SearchResult(BaseModel):
    url: str
    title: str
    snippet: str

class SearchResponse(BaseModel):
    query: str
    did_you_mean: Optional[str] = None
    total_time_ms: int
    total_hits: int
    page: int
    total_pages: int
    results: List[SearchResult]

@app.get("/api/search", response_model=SearchResponse)
async def search(q: str, page: int = 1, page_size: int = 15):
    if not q:
        raise HTTPException(status_code=400, detail="Query cannot be empty")
        
    if not os.path.exists(INDEX_DIR):
        raise HTTPException(status_code=500, detail="Search index not found. Run crawler first.")

    start_time = time.perf_counter()
    results_list = []
    did_you_mean = None
    total_hits = 0
    total_pages = 0
    
    try:
        ix = open_dir(INDEX_DIR)
        qparser = QueryParser("content", schema=ix.schema)
        query_obj = qparser.parse(q)
        
        with ix.searcher() as searcher:
            # Spelling Correction (Did you mean?)
            corrector = searcher.corrector("content")
            corrected = corrector.suggest(q, limit=1)
            
            # If the best suggestion isn't exactly what was typed, offer it
            if corrected and corrected[0] != q.lower():
                did_you_mean = corrected[0]
            
            # Perform Search with Pagination
            # Fetch `page_size` results starting from `(page - 1) * page_size`
            # Using search_page is optimal for Whoosh
            results_page = searcher.search_page(query_obj, page, pagelen=page_size)
            total_hits = len(results_page)
            total_pages = results_page.pagecount
            
            for hit in results_page:
                # Generate a highlighted HTML snippet using Whoosh
                snippet = hit.highlights("content", text=hit.get("content"))
                if not snippet:
                    snippet = hit.get('title', 'No snippet available')
                
                results_list.append(SearchResult(
                    url=hit.get("url", ""),
                    title=hit.get("title", "No Title"),
                    snippet=snippet
                ))
    except ValueError:
        # Happens if requested page > total_pages
        pass
    except Exception as e:
        print(f"Search API error: {e}")
        raise HTTPException(status_code=500, detail="Error executing search query")
        
    end_time = time.perf_counter()
    duration_ms = int((end_time - start_time) * 1000)

    return SearchResponse(
        query=q,
        did_you_mean=did_you_mean,
        total_time_ms=duration_ms,
        total_hits=total_hits,
        page=page,
        total_pages=total_pages,
        results=results_list
    )

@app.get("/api/suggest")
async def suggest(q: str):
    """Provides autocomplete suggestions as the user types."""
    if not q or len(q) < 2:
        return []
        
    suggestions = []
    try:
        ix = open_dir(INDEX_DIR)
        with ix.reader() as reader:
            # Expand the prefix to match stored terms in the index
            for word in reader.expand_prefix("content", q.lower()):
                suggestions.append(word.decode('utf-8'))
                if len(suggestions) >= 5: # Limit to top 5 suggestions
                    break
    except Exception:
        pass
        
    return suggestions

@app.get("/api/stats")
async def get_stats():
    """Return some cool stats for the frontend dashboard."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT COUNT(*) FROM pages") as cursor:
                pages = await cursor.fetchone()
            async with db.execute("SELECT COUNT(*) FROM discovered_links") as cursor:
                links = await cursor.fetchone()
                
        return {
            "indexed_pages": pages[0] if pages else 0,
            "discovered_links": links[0] if links else 0
        }
    except Exception as e:
        print(f"Stats API error: {e}")
        return {"indexed_pages": 0, "discovered_links": 0}

class CrawlRequest(BaseModel):
    url: str

@app.post("/api/crawl")
async def trigger_crawl(req: CrawlRequest, background_tasks: BackgroundTasks):
    """Submits a URL to be crawled in the background."""
    if not req.url or not req.url.startswith("http"):
        raise HTTPException(status_code=400, detail="Invalid URL provided")
        
    try:
        manager = CrawlerManager.get_manager(DB_PATH)
        # Enqueue the background task
        background_tasks.add_task(manager.crawl_single, req.url)
        return {"status": "success", "message": f"Crawling started for {req.url}"}
    except Exception as e:
        print(f"Error starting crawl: {e}")
        raise HTTPException(status_code=500, detail="Failed to start crawler")

if __name__ == "__main__":
    import uvicorn
    # Run the server on port 8080 to avoid common WinError 10013 collisions
    uvicorn.run("api:app", host="0.0.0.0", port=8080, reload=True)
