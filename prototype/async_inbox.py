"""Provides a typed inbox for use in `asyncio` coroutines and tasks"""

# Core dependencies
import asyncio
from typing import Generic, TypeVar, final

MessageType = TypeVar("MessageType")


@final
class AsyncInbox(Generic[MessageType]):
    """A typed inbox that is for use in `async` tasks to send messages
    back and forth. The read is intentionally blocking, to mimic actor
    communication. Thus, it is important that the `read` coroutine is ran
    in an individual tasks, as awaiting it will block the task.
    """

    def __init__(self, maxsize: int = 0) -> None:
        """The `AsyncInbox` is simply a wrapper over the core `asyncio.Queue`"""
        self.__queue: asyncio.Queue = asyncio.Queue(maxsize)

    @final
    def send(self, message: MessageType) -> None:
        """Send a message immediately to the inbox"""
        self.__queue.put_nowait(message)

    @final
    async def read(self) -> MessageType:
        """Block on the inbox until a message is received and then return
        that message. It is best to run this inside a task, as it blocks
        the coroutine that it is awaited on.
        """
        message = await self.__queue.get()
        return message
