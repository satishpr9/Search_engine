import abc
import asyncio
from typing import Any, Callable, Dict, List

class MessageQueue(abc.ABC):
    @abc.abstractmethod
    async def publish(self, topic: str, message: Dict[str, Any]):
        pass

    @abc.abstractmethod
    async def subscribe(self, topic: str, handler: Callable[[Dict[str, Any]], Any]):
        pass

class MemoryMessageQueue(MessageQueue):
    """
    In-memory message queue using asyncio.Queue for local testing and development.
    In production, replace this with a RabbitMQ or Kafka implementation.
    """
    def __init__(self):
        self._queues: Dict[str, asyncio.Queue] = {}
        self._handlers: Dict[str, List[Callable]] = {}
        self._tasks = []

    def _get_queue(self, topic: str) -> asyncio.Queue:
        if topic not in self._queues:
            self._queues[topic] = asyncio.Queue()
        return self._queues[topic]

    async def publish(self, topic: str, message: Dict[str, Any]):
        q = self._get_queue(topic)
        await q.put(message)

    async def _worker(self, topic: str, q: asyncio.Queue):
        while True:
            try:
                message = await q.get()
                handlers = self._handlers.get(topic, [])
                for handler in handlers:
                    # Run handlers concurrently
                    asyncio.create_task(handler(message))
                q.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error processing message from topic {topic}: {e}")

    async def subscribe(self, topic: str, handler: Callable[[Dict[str, Any]], Any]):
        if topic not in self._handlers:
            self._handlers[topic] = []
            q = self._get_queue(topic)
            task = asyncio.create_task(self._worker(topic, q))
            self._tasks.append(task)
            
        self._handlers[topic].append(handler)
        print(f"Subscribed to topic: {topic}")
