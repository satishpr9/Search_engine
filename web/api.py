from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional
from whoosh.index import open_dir
from whoosh.qparser import QueryParser, MultifieldParser
import os
import aiosqlite
import time
import asyncio
import json
from dotenv import load_dotenv

from wiki import fetch_knowledge_panel

import re
import ast
import operator
import httpx

def evaluate_math(expr: str):
    allowed_operators = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.BitXor: operator.xor,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos
    }

    def _eval(node):
        if hasattr(ast, 'Constant') and isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.Num):
            return node.n
        elif isinstance(node, ast.BinOp):
            return allowed_operators[type(node.op)](_eval(node.left), _eval(node.right))
        elif isinstance(node, ast.UnaryOp):
            return allowed_operators[type(node.op)](_eval(node.operand))
        else:
            raise TypeError(node)
            
    try:
        expr_clean = expr.replace('^', '**')
        # double check to avoid evaluating dangerous code
        if not re.match(r'^[\d\+\-\*\/\(\)\.\^\s]+$', expr_clean):
            return None
        node = ast.parse(expr_clean, mode='eval').body
        result = _eval(node)
        
        if isinstance(result, float) and result.is_integer():
            result = int(result)
        elif isinstance(result, float):
            result = round(result, 6)
            
        return {
            "type": "calculator",
            "expression": expr,
            "result": str(result)
        }
    except Exception:
        return None

async def fetch_weather(location: str):
    try:
        async with httpx.AsyncClient() as client:
            geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={location}&count=1&language=en&format=json"
            geo_res = await client.get(geo_url, timeout=3.0)
            if geo_res.status_code == 200:
                geo_data = geo_res.json()
                if geo_data.get("results"):
                    result = geo_data["results"][0]
                    lat, lon = result["latitude"], result["longitude"]
                    name = result["name"]
                    
                    weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,weather_code&temperature_unit=celsius"
                    w_res = await client.get(weather_url, timeout=3.0)
                    if w_res.status_code == 200:
                        w_data = w_res.json()
                        current = w_data.get("current", {})
                        temp = current.get("temperature_2m")
                        code = current.get("weather_code", 0)
                        
                        desc = "Clear"
                        if code in [1,2,3]: desc = "Partly Cloudy"
                        elif code in [45,48]: desc = "Fog"
                        elif code in [51,53,55,56,57]: desc = "Drizzle"
                        elif code in [61,63,65,66,67]: desc = "Rain"
                        elif code in [71,73,75,77]: desc = "Snow"
                        elif code in [80,81,82]: desc = "Rain Showers"
                        elif code in [85,86]: desc = "Snow Showers"
                        elif code in [95,96,99]: desc = "Thunderstorm"
                        
                        return {
                            "type": "weather",
                            "location": name,
                            "temperature": f"{round(temp)}°C" if temp is not None else "--",
                            "condition": desc
                        }
    except Exception:
        pass
    return None

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, ".env"))

# Attempt to load Groq client
try:
    from groq import AsyncGroq
    groq_client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY")) if os.getenv("GROQ_API_KEY") else None
except ImportError:
    groq_client = None

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
    thumbnail_url: Optional[str] = None

class SearchResponse(BaseModel):
    query: str
    did_you_mean: Optional[str] = None
    ai_summary: Optional[str] = None
    knowledge_panel: Optional[dict] = None
    image_results: Optional[List[dict]] = None
    widget: Optional[dict] = None
    total_time_ms: int
    total_hits: int
    page: int
    total_pages: int
    results: List[SearchResult]

@app.get("/api/search", response_model=SearchResponse)
async def search(q: str, page: int = 1, page_size: int = 15, type: str = "all"):
    if not q:
        raise HTTPException(status_code=400, detail="Query cannot be empty")
        
    if not os.path.exists(INDEX_DIR):
        print("Search index not found. Please run the crawler first.")

    print(f"DEBUG: Searching for '{q}'")
    start_time = time.perf_counter()
    results_list = []
    did_you_mean = None
    total_hits = 0
    total_pages = 0
    widget = None
    
    if page == 1:
        # Check Math
        math_str = q.strip()
        if re.match(r'^[\d\+\-\*\/\(\)\.\^\s]+$', math_str) and any(op in math_str for op in '+-*/^'):
            widget = evaluate_math(math_str)
            
        # Check Weather
        if not widget:
            # Fix: Using re.IGNORECASE flag instead of inline (?i) for better compatibility
            weather_match = re.match(r'^weather\s+(?:in|for|at\s+)?(.+)$', math_str, re.IGNORECASE)
            if weather_match:
                widget = await fetch_weather(weather_match.group(1).strip())
    
    # Delete specialized DDGS placeholders for types
    # specialized logic moves entirely into Whoosh Search
    
    # To make search "Google-fast", we launch independent fetches in parallel
    async def run_whoosh_search():
        nonlocal did_you_mean, total_hits, total_pages
        local_results = []
        try:
            # We run the blocking Whoosh parts in a thread to keep the event loop free
            def _sync_whoosh():
                res_list = []
                dy_mean = None
                t_hits = 0
                t_pages = 0
                try:
                    ix = open_dir(INDEX_DIR)
                    qparser = MultifieldParser(["title", "content"], schema=ix.schema)
                    query_obj = qparser.parse(q)
                    
                    with ix.searcher() as searcher:
                        corrector = searcher.corrector("content")
                        sug = corrector.suggest(q, limit=1)
                        if sug and sug[0] != q.lower():
                            dy_mean = sug[0]
                            
                        # Apply custom filters for specialized tabs
                        raw_results = []
                        if type == "images":
                            # Pull all matching query results first, filter later
                            raw_results = searcher.search(query_obj, limit=None)
                            # Filter results locally to ensure they have an image
                            filtered = [hit for hit in raw_results if hit.get("thumbnail_url")]
                            t_hits = len(filtered)
                            t_pages = max(1, (t_hits + page_size - 1) // page_size)
                            # Apply pagination manually here since we post-filtered
                            start_idx = (page - 1) * page_size
                            page_hits = filtered[start_idx:start_idx + page_size]
                        elif type == "videos":
                            from whoosh.query import Term, And
                            # Search query AND page_type=video
                            video_query = And([query_obj, Term("page_type", "video")])
                            results_page = searcher.search_page(video_query, page, pagelen=page_size)
                            t_hits = len(results_page)
                            t_pages = results_page.pagecount
                            page_hits = results_page
                        elif type == "news":
                            from whoosh.query import Term, And
                            news_query = And([query_obj, Term("page_type", "article")])
                            results_page = searcher.search_page(news_query, page, pagelen=page_size)
                            t_hits = len(results_page)
                            t_pages = results_page.pagecount
                            page_hits = results_page
                        else:
                            # Standard all search
                            results_page = searcher.search_page(query_obj, page, pagelen=page_size)
                            t_hits = len(results_page)
                            t_pages = results_page.pagecount
                            page_hits = results_page
                        
                        for hit in page_hits:
                            snippet = ""
                            if hasattr(hit, 'highlights'):
                                snippet = hit.highlights("content", text=hit.get("content"))
                            if not snippet: snippet = hit.get('title', 'No snippet available')
                            
                            import re
                            snippet = re.sub(r'<(/?)(img|iframe|video|script|style|div|span|p|a)[^>]*>', '', snippet, flags=re.IGNORECASE)
                            
                            res_list.append(SearchResult(
                                url=hit.get("url", ""),
                                title=hit.get("title", "No Title"),
                                snippet=snippet,
                                thumbnail_url=hit.get("thumbnail_url", "")
                            ))
                except: pass
                return res_list, dy_mean, t_hits, t_pages

            local_results, did_you_mean, total_hits, total_pages = await asyncio.to_thread(_sync_whoosh)
        except: pass
        return local_results

    # Launch Whoosh search task
    whoosh_task = asyncio.create_task(run_whoosh_search())

    # Wait for Whoosh results
    results_list = await whoosh_task
    
    total_hits = max(total_hits, len(results_list))
    total_pages = max(total_pages, 1)

    ai_summary = None

    end_time = time.perf_counter()
    duration_ms = int((end_time - start_time) * 1000)
    
    knowledge_panel = None
    if page == 1 and type == "all":
        knowledge_panel = await fetch_knowledge_panel(q)
        
    image_results = None
    # For horizontal carousel on generic 'All' tab, extract top items with images dynamically
    if type == "all" and results_list:
        with_images = [r for r in results_list if r.thumbnail_url]
        if with_images:
            image_results = [{"title": r.title, "image": r.thumbnail_url, "url": r.url} for r in with_images[:10]]

    return SearchResponse(
        query=q,
        did_you_mean=did_you_mean,
        ai_summary=ai_summary,
        knowledge_panel=knowledge_panel,
        image_results=image_results,
        widget=widget,
        total_time_ms=duration_ms,
        total_hits=total_hits,
        page=page,
        total_pages=total_pages,
        results=results_list
    )

class StreamRequest(BaseModel):
    query: str
    context: str

@app.post("/api/stream_ai")
async def stream_ai(req: StreamRequest):
    """Streams AI generated summary using Server-Sent Events (SSE)."""
    
    prompt = f"""
    You are an AI Search Assistant for the Icro Search Engine.
    Use ONLY the following search results to answer the user's query.
    Keep your answer detailed, structured, and highly informative (write about 5 to 6 lines or a detailed paragraph).
    If the search results do not contain enough information to answer the query, say you don't have enough context.
    
    Query: {req.query}
    
    Search Results Context:
    {req.context}
    """

    async def generate_groq():
        try:
            stream = await groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.1-8b-instant",
                temperature=0.3,
                max_tokens=600,
                stream=True
            )
            async for chunk in stream:
                content = chunk.choices[0].delta.content
                if content:
                    yield f"data: {json.dumps({'text': content})}\n\n"
        except Exception as e:
            print(f"Groq stream error: {e}")
            yield f"data: {json.dumps({'error': 'Failed to generate AI summary.'})}\n\n"
        yield "data: [DONE]\n\n"
        
    def generate_ollama():
        try:
            import ollama
            stream = ollama.chat(model='llama3', messages=[
                {'role': 'user', 'content': prompt}
            ], stream=True)
            for chunk in stream:
                content = chunk['message']['content']
                if content:
                    yield f"data: {json.dumps({'text': content})}\n\n"
        except Exception as e:
            print(f"Ollama stream error: {e}")
            yield f"data: {json.dumps({'error': 'Failed to generate AI summary.'})}\n\n"
        yield "data: [DONE]\n\n"
        
    if groq_client:
        return StreamingResponse(generate_groq(), media_type="text/event-stream")
    else:
        return StreamingResponse(generate_ollama(), media_type="text/event-stream")

class ChatRequest(BaseModel):
    query: str
    context: str
    history: str # The previous AI summary

@app.post("/api/chat")
async def chat_ai(req: ChatRequest):
    """Streams a follow-up answer using Server-Sent Events (SSE)."""
    
    prompt = f"""
    You are an AI Search Assistant for the Icro Search Engine.
    The user is asking a follow-up question based on their original search.
    Use the provided Search Results and the Previous AI Summary to answer the new question.
    Keep your answer detailed, structured, and highly informative.
    
    Original Search Results Context:
    {req.context}
    
    Previous AI Summary:
    {req.history}
    
    User's Follow-up Question: {req.query}
    """

    async def generate_groq():
        try:
            stream = await groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.1-8b-instant",
                temperature=0.3,
                max_tokens=600,
                stream=True
            )
            async for chunk in stream:
                content = chunk.choices[0].delta.content
                if content:
                    yield f"data: {json.dumps({'text': content})}\n\n"
        except Exception as e:
            print(f"Groq chat error: {e}")
            yield f"data: {json.dumps({'error': 'Failed to generate chat response.'})}\n\n"
        yield "data: [DONE]\n\n"
        
    def generate_ollama():
        try:
            import ollama
            stream = ollama.chat(model='llama3', messages=[
                {'role': 'user', 'content': prompt}
            ], stream=True)
            for chunk in stream:
                content = chunk['message']['content']
                if content:
                    yield f"data: {json.dumps({'text': content})}\n\n"
        except Exception as e:
            print(f"Ollama chat error: {e}")
            yield f"data: {json.dumps({'error': 'Failed to generate chat response.'})}\n\n"
        yield "data: [DONE]\n\n"
        
    if groq_client:
        return StreamingResponse(generate_groq(), media_type="text/event-stream")
    else:
        return StreamingResponse(generate_ollama(), media_type="text/event-stream")

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

@app.websocket("/api/ws/admin")
async def websocket_admin_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            try:
                # Fetch live stats from the active crawler schema
                async with aiosqlite.connect(DB_PATH) as db:
                    async with db.execute("SELECT COUNT(*) FROM raw_pages") as cursor:
                        pages = await cursor.fetchone()
                        
                # Get DB file size in MB
                db_size_mb = 0
                if os.path.exists(DB_PATH):
                    db_size_mb = round(os.path.getsize(DB_PATH) / (1024 * 1024), 2)
                
                payload = {
                    "indexed_pages": pages[0] if pages else 0,
                    "discovered_links": "In Memory",
                    "db_size_mb": db_size_mb,
                    "status": "online",
                    "timestamp": time.time()
                }
                
                await websocket.send_json(payload)
            except Exception as e:
                print(f"WS DB Error: {e}")
                
            await asyncio.sleep(2) # Stream updates every 2 seconds
            
    except WebSocketDisconnect:
        print("Admin client disconnected from WebSocket.")

if __name__ == "__main__":
    import uvicorn
    # Run the server on port 8080 to avoid common WinError 10013 collisions
    uvicorn.run("api:app", host="0.0.0.0", port=8080, reload=True)
