# Core dependencies
from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Any, final

# Project dependencies
from prototype.async_inbox import AsyncInbox


MessageType = TypeVar("MessageType")


class AsyncWorker(Generic[MessageType], ABC):
    def __init__(self):
        self.__inbox = AsyncInbox[MessageType]()
        self.__keep_running = True
        self.__is_initialized = False
        self.__is_shutdown = False

    @property
    def is_initialized(self) -> bool:
        return self.__is_initialized

    @property
    def is_shutdown(self) -> bool:
        return self.__is_shutdown

    @abstractmethod
    async def _initialize(self) -> None: ...

    @abstractmethod
    async def _shutdown(self) -> None: ...

    @abstractmethod
    async def _receive_message(self, message: MessageType) -> None: ...

    @final
    async def run(self) -> None:
        try:
            await self._initialize()
            self.__is_initialized = True

            while self.__keep_running:
                message: MessageType = await self.__inbox.read()
                await self._receive_message(message)
        finally:
            await self._shutdown()
            self.__is_shutdown = True

    @final
    def schedule_shutdown(self) -> None:
        self.__keep_running = False

    @final
    def send(self, message: MessageType) -> None:
        self.__inbox.send(message)
