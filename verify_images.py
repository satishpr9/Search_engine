import sqlite3
import pandas as pd

def check_images():
    conn = sqlite3.connect("crawler_data.db")
    try:
        df = pd.read_sql_query("SELECT * FROM images LIMIT 10", conn)
        print("\n=== Extracted Images (Top 10) ===")
        print(df)
        
        count = pd.read_sql_query("SELECT COUNT(*) as count FROM images", conn)
        print(f"\nTotal images found: {count['count'][0]}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    check_images()
