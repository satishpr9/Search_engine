import asyncio
import sys
import os

# Ensure we can import web.api
sys.path.append(os.path.abspath('web'))
from api import search

async def run_tests():
    print("Testing 'all' search...")
    res_all = await search("youtube", page=1, page_size=10, type="all")
    print(f"  Got {res_all.total_hits} total hits. First 3:")
    for r in res_all.results[:3]:
        print(f"    - {r.title} (Image={r.thumbnail_url})")
        
    print("\nTesting 'images' search...")
    res_img = await search("youtube", page=1, page_size=10, type="images")
    print(f"  Got {res_img.total_hits} total hits. All of them should have thumbnails.")
    for r in res_img.results[:3]:
        print(f"    - {r.title} (Image={r.thumbnail_url})")

    print("\nTesting 'videos' search...")
    res_vid = await search("youtube", page=1, page_size=10, type="videos")
    print(f"  Got {res_vid.total_hits} total hits. These should be video pages.")
    for r in res_vid.results[:3]:
        print(f"    - {r.title} (URL={r.url})")

if __name__ == "__main__":
    asyncio.run(run_tests())
