from typing import Dict, Any
from agents.base_agent import BaseAgent
from infrastructure.message_queue import MessageQueue
from infrastructure.raw_db import RawDB

class ImageAgent(BaseAgent):
    """
    Listens for extracted image metadata and saves it to the RawDB.
    """
    def __init__(self, mq: MessageQueue, raw_db: RawDB):
        super().__init__(mq, "ImageAgent")
        self.raw_db = raw_db

    def get_listen_topic(self) -> str:
        return "image_queue"

    async def process_message(self, message: Dict[str, Any]):
        url = message.get("url")
        page_url = message.get("page_url")
        description = message.get("description", "")
        
        if not url or not page_url:
            return
            
        self.logger.info(f"Saving image metadata: {url} (from {page_url})")
        success = await self.raw_db.save_image(url, page_url, description)
        
        if success:
            self.logger.info(f"Successfully saved image {url}")
        else:
            self.logger.error(f"Failed to save image {url}")
