import abc
import asyncio
import logging
from typing import Dict, Any
from infrastructure.message_queue import MessageQueue

class BaseAgent(abc.ABC):
    """
    Base class for all autonomous agents in the pipeline.
    Each agent should define its primary queue to listen to
    and implement the process_message method.
    """
    def __init__(self, mq: MessageQueue, name: str):
        self.mq = mq
        self.name = name
        self.logger = logging.getLogger(name)
        if not self.logger.handlers:
            logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")

    @abc.abstractmethod
    def get_listen_topic(self) -> str:
        """Return the topic this agent listens to. Return None if it's an edge agent (like Answer Agent)"""
        pass

    @abc.abstractmethod
    async def process_message(self, message: Dict[str, Any]):
        """Process an incoming message from the topic"""
        pass

    async def start(self):
        topic = self.get_listen_topic()
        if topic:
            await self.mq.subscribe(topic, self.process_message)
            self.logger.info(f"Started and listening to topic: {topic}")
        else:
            self.logger.info("Started (no active queue subscription)")
