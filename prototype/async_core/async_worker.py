# Core dependencies
from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Any, final, override

# Project dependencies
from prototype.async_core.messaging import AsyncInbox, ReplyChannel
from prototype.async_core.mixins import AsyncLoggingMixin

MessageType = TypeVar("MessageType")
ReplyType = TypeVar("ReplyType")


class AsyncWorker(Generic[MessageType], AsyncLoggingMixin, ABC):
    def __init__(self, name: str = ""):
        self.__name = name
        self.__inbox = AsyncInbox[MessageType](name=name)
        self.__keep_running = True
        self.__is_initialized = False
        self.__is_shutdown = False

    @override
    def _async_log_name(self) -> str:
        if self.__name:
            return f"<AsyncWorker: {self.__name}"
        else:
            return f"{self}"

    @property
    def inbox(self) -> AsyncInbox[MessageType]:
        return self.__inbox

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

    @abstractmethod
    async def _receive_synchronous_message[ReplyType](self, message: MessageType, reply_channel: ReplyChannel[ReplyType]) -> None: ...  # type: ignore

    @final
    async def run(self) -> None:
        try:
            await self._initialize()
            self.__is_initialized = True
            self._async_log_debug(f"Initialized")

            while self.__keep_running:
                self._async_log_debug(f"Waiting on message")

                msg: MessageType | tuple[MessageType, ReplyChannel] = await self.__inbox.read()

                self._async_log_debug(f'Received message "{msg}"')

                match msg:
                    case (message, reply_channel):
                        await self._receive_synchronous_message(message, reply_channel)
                    case message:
                        await self._receive_message(message)

        except Exception as exception:
            await self._shutdown()
            self.__is_shutdown = True
            self._async_log_debug(f"Shutdown")

    @final
    def schedule_shutdown(self) -> None:
        self.__keep_running = False

    @final
    def send(self, message: MessageType) -> None:
        self.__inbox.send(message)
