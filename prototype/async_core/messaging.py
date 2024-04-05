"""Provides a typed inbox for use in `asyncio` coroutines and tasks"""

# Core dependencies
# The `__future__` import must be listed first. Otherwise, a `SyntaxError` is emitted.
from __future__ import annotations
import asyncio
from typing import Generic, TypeVar, Any, final, override

# Project dependencies
from prototype.async_core.mixins import AsyncLoggingMixin


Message = TypeVar("Message")


@final
class AsyncInbox(Generic[Message], AsyncLoggingMixin):
    """A typed inbox that is for use in `async` tasks to send messages
    back and forth. The read is intentionally blocking, to mimic actor
    communication. Thus, it is important that the `read` coroutine is ran
    in an individual tasks, as awaiting it will block the task.
    """

    def __init__(self, name: str = "", maxsize: int = 0) -> None:
        """The `AsyncInbox` is simply a wrapper over the core `asyncio.Queue`"""
        self.__name = name
        self.__queue: asyncio.Queue = asyncio.Queue(maxsize)

    @override  # for AsyncLoggingMixin
    def async_log_name(self) -> str:
        if self.__name:
            return f"<AsyncInbox: {self.__name}>"
        else:
            return f"{self}"

    def send(self, message: Message) -> None:
        """Send a message immediately to the inbox"""
        self.__queue.put_nowait(message)
        self.async_log_debug(f"<Message: {message}> was sent to inbox")

    async def send_synchronous(self, message: Message) -> Any:
        """Sends a message immediately and synchronously to the inbox. This means that
        the caller is expecting a reply and will not continue until the reply arrives.
        Currently, it is up to the sender to know what type to expect back.
        """
        reply_channel = ReplyChannel[Any]()
        self.__queue.put_nowait((message, reply_channel))
        return await reply_channel.read_reply()

    async def read(self) -> Message | tuple[Message, ReplyChannel]:
        """Block on the inbox until a message is received and then return
        that message. It is best to run this inside a task, as it blocks
        the coroutine that it is awaited on.
        """
        self.async_log_debug("Waiting for a message")
        message = await self.__queue.get()
        self.async_log_debug(f"<Message: {message}> was read from inbox")
        return message


@final
class ReplyChannel(Generic[Message]):
    """A typed inbox that is for use in `async` tasks to send messages
    back and forth. The read is intentionally blocking, to mimic actor
    communication. Thus, it is important that the `read` coroutine is ran
    in an individual tasks, as awaiting it will block the task.
    """

    def __init__(self) -> None:
        """The `ReplyChannel` is simply a wrapper over the core `asyncio.Queue`
        with a maximum size set to 1
        """
        # A maximum size of 1 is set because this is only used to put the result of a single
        # message on the queue to be immediately read.
        self.__queue: asyncio.Queue = asyncio.Queue(1)

    def reply(self, message: Message) -> None:
        """Reply with the message"""
        self.__queue.put_nowait(message)

    async def read_reply(self) -> Message:
        """Read the reply that was sent to the channel"""
        return await self.__queue.get()
