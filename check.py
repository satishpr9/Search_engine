import asyncio
import aiosqlite

async def check_db():
    async with aiosqlite.connect('crawler_data.db') as db:
        async with db.execute('SELECT COUNT(*) FROM pages') as cursor:
            pages = await cursor.fetchone()
            print(f'Pages: {pages[0]}')
            
        async with db.execute('SELECT COUNT(*) FROM discovered_links') as cursor:
            links = await cursor.fetchone()
            print(f'Links: {links[0]}')
            
        async with db.execute('SELECT COUNT(*) FROM crawl_logs') as cursor:
            logs = await cursor.fetchone()
            print(f'Logs: {logs[0]}')

asyncio.run(check_db())
