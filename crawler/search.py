import argparse
import sys
from whoosh.index import open_dir
from whoosh.qparser import QueryParser
import os

INDEX_DIR = "whoosh_index"

def search(query_str):
    if not os.path.exists(INDEX_DIR):
        print("Search index does not exist. Please run the crawler first.")
        sys.exit(1)
        
    try:
        ix = open_dir(INDEX_DIR)
        
        # We want to search primarily the page content
        qparser = QueryParser("content", schema=ix.schema)
        
        query = qparser.parse(query_str)
        
        with ix.searcher() as searcher:
            # Get the top 10 results
            results = searcher.search(query, limit=10)
            
            print(f"\nFound {len(results)} results for '{query_str}':\n")
            
            if not results:
                print("No matches found.")
                return
                
            for i, result in enumerate(results, 1):
                url = result.get('url', 'Unknown URL')
                title = result.get('title', 'No Title')
                
                print(f"{i}. {title}")
                print(f"   {url}")
                print("-" * 50)
                
    except Exception as e:
        print(f"Error during search: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Search the local Web Crawler index.")
    parser.add_argument("query", type=str, help="Search query string")
    
    args = parser.parse_args()
    search(args.query)
