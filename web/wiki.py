import httpx
import asyncio
from bs4 import BeautifulSoup

async def fetch_quick_facts(formatted_query: str):
    url = f"https://en.wikipedia.org/wiki/{formatted_query}"
    headers = {
        "User-Agent": "IcroSearchEngine/1.0 (contact@example.com)"
    }
    
    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(url, headers=headers, timeout=3.0)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                infobox = soup.find('table', class_=lambda c: c and 'infobox' in c)
                if not infobox:
                    return None
                
                facts = {}
                rows = infobox.find_all('tr')
                count = 0
                for row in rows:
                    if count >= 6: # Limit to 6 facts
                        break
                    th = row.find('th', class_='infobox-label')
                    td = row.find('td', class_='infobox-data')
                    
                    if not (th and td):
                        # Sometimes th and td don't have these exact classes, fallback
                        th = row.find('th')
                        td = row.find('td')
                        
                    if th and td:
                        key = th.get_text(strip=True)
                        
                        # Remove citations [1], [2]
                        for sup in td.find_all('sup'):
                            sup.decompose()
                            
                        # Remove style blocks
                        for style in td.find_all('style'):
                            style.decompose()
                            
                        # Use a nice separator for lists (e.g. <br> tags)
                        val = td.get_text(separator=', ', strip=True)
                        
                        # Clean up any trailing commas or long texts
                        if key and val and len(val) < 120:
                            facts[key] = val
                            count += 1
                            
                return facts if facts else None
    except Exception as e:
        print(f"Error in fetch_quick_facts: {e}")
        pass
    return None


async def fetch_knowledge_panel(query: str):
    """
    Attempts to fetch a Wikipedia summary for the given query.
    Returns a dictionary with 'title', 'extract', 'thumbnail_url', 'url' and optionally 'quick_facts'.
    Returns None if not found or on error.
    """
    if not query:
        return None
        
    formatted_query = query.strip().replace(" ", "_").title()
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{formatted_query}"
    
    headers = {
        "User-Agent": "IcroSearchEngine/1.0 (contact@example.com)"
    }
    
    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(url, headers=headers, timeout=3.0)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("type") == "disambiguation":
                    return None
                    
                panel_data = {
                    "title": data.get("title", ""),
                    "extract": data.get("extract", ""),
                    "url": data.get("content_urls", {}).get("desktop", {}).get("page", ""),
                    "image_url": data.get("thumbnail", {}).get("source", "")
                }
                
                if panel_data["extract"]:
                    # Try fetching quick facts in parallel or sequentially
                    # For simplicity, sequential here as it's quick
                    quick_facts = await fetch_quick_facts(formatted_query)
                    if quick_facts:
                        panel_data["facts"] = quick_facts
                        
                    # Fetch related pages (simulate "Things to do")
                    try:
                        related_url = f"https://en.wikipedia.org/api/rest_v1/page/related/{formatted_query}"
                        related_res = await client.get(related_url, headers=headers, timeout=3.0)
                        if related_res.status_code == 200:
                            related_data = related_res.json()
                            related_pages = related_data.get("pages", [])
                            related_entities = []
                            for page in related_pages[:5]:
                                if page.get("type") != "disambiguation":
                                    related_entities.append({
                                        "title": page.get("title", "").replace("_", " "),
                                        "description": page.get("description", ""),
                                        "image_url": page.get("thumbnail", {}).get("source", ""),
                                        "url": page.get("content_urls", {}).get("desktop", {}).get("page", "")
                                    })
                            if related_entities:
                                panel_data["related_entities"] = related_entities
                    except Exception as re_err:
                        print(f"Error fetching related pages for '{query}': {re_err}")
                    
                    return panel_data
            
            return None
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error fetching knowledge panel for '{query}': {e}")
        return None

if __name__ == "__main__":
    async def test():
        res = await fetch_knowledge_panel("India")
        print(res)
        res2 = await fetch_knowledge_panel("Elon Musk")
        print(res2)
    asyncio.run(test())
