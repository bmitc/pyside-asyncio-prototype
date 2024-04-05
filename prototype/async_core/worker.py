"""Provides a generic worker class to be used inside an `asyncio` event loop.
The worker class is to help manage initialization, running, and shutting down
of whatever it is that the worker manages.
"""

# Core dependencies
from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Any, final, override

# Project dependencies
from prototype.async_core.messaging import AsyncInbox, ReplyChannel
from prototype.async_core.mixins import AsyncLoggingMixin


Message = TypeVar("Message")


class AsyncWorker(Generic[Message], AsyncLoggingMixin, ABC):
    """A generic worker that manages an inbox of the specific generic type. Other coroutines,
    tasks, workers, etc. in an event loop can send messages to this worker via the `send` method
    or directly via the `inbox` property. The worker will then receive and process the message.
    The specific initializing, shutdown, and processing of messages is up to a concrete
    implementation of this class.
    """

    def __init__(self, name: str = ""):
        self.__name = name
        self.__inbox = AsyncInbox[Message](name=name)
        self.__keep_running = True
        self.__is_initialized = False
        self.__is_shutdown = False

    @override  # for AsyncLoggingMixin
    def async_log_name(self) -> str:
        if self.__name:
            return f"<AsyncWorker: {self.__name}"
        else:
            return f"{self}"

    @property
    def inbox(self) -> AsyncInbox[Message]:
        """The worker's inbox"""
        return self.__inbox

    @property
    def is_initialized(self) -> bool:
        """Indicates whether the worker has been initialized or not"""
        return self.__is_initialized

    @property
    def is_shutdown(self) -> bool:
        """Indicates whether the worker has been shutdown or not"""
        return self.__is_shutdown

    @abstractmethod
    async def _initialize(self) -> None:
        """Initializes any of the underlying worker's clients or other dependencies.
        A concrete implementation must override this method. Any initialization of the worker
        that performs any awaiting of coroutines or any non-trivial work should go in this
        method and not `__init__`. If there is no initialization to be performed, then simply
        place `pass` in the method implementation.
        """
        ...

    @abstractmethod
    async def _shutdown(self) -> None:
        """Shuts down any of the underlying worker's clients or other dependencies.
        A concrete implementation must override this method. If there is no initialization
        to be performed, then simply place `pass` in the method implementation.
        """
        ...

    @abstractmethod
    async def _receive_message(self, message: Message) -> None:
        """When a message is sent to the worker's internal inbox, this method is called with the
        received message. Concrete implementations should override this method, as it is the only
        way for a worker to take action.
        """
        ...

    @abstractmethod
    async def _receive_synchronous_message(
        self, message: Message, reply_channel: ReplyChannel[Any]
    ) -> None:
        """When a synchronous message is sent to the worker's internal inbox, this method is called
        with the received message. Concrete implementations should override this method, as it is
        the only way for a worker to take action. The override should use the given
        `ReplyChannel`'s `reply` method to reply back to the sender with a response.
        """
        ...

    @final
    async def run(self) -> None:
        """Runs a loop that listens for a message on every iteration. When the message arrives, the
        message is processed via the override of `self._receive_message`.
        """
        try:
            await self._initialize()
            self.__is_initialized = True
            self.async_log_debug("Initialized")

            while self.__keep_running:
                self.async_log_debug("Waiting on message")

                msg = await self.__inbox.read()

                self.async_log_debug(f'Received message "{msg}"')

                match msg:
                    case (message, reply_channel):
                        await self._receive_synchronous_message(message, reply_channel)  # type: ignore, pylint: disable=line-too-long
                    case message:
                        await self._receive_message(message)  # type: ignore

        except Exception as exception:  # pylint: disable=broad-exception-caught
            self.async_log_debug(f"Exception: {exception}")
            await self._shutdown()
            self.__is_shutdown = True
            self.async_log_debug("Shutdown")

    @final
    def schedule_shutdown(self) -> None:
        """Schedules the worker to shutdown, which means that it's internal `run` loop
        will stop on the next opportunity, and then the `_shutdown` method will be called.
        """
        self.__keep_running = False

    @final
    def send(self, message: Message) -> None:
        """A convenience method to send a message to the worker's inbox. The worker's inbox
        can also be retrieved using the `inbox` property.
        """
        self.__inbox.send(message)

    @final
    async def send_synchronous(self, message: Message) -> Any:
        """A convenience method to send a message immediately and synchronously to the worker's
        inbox. This means that the caller is expecting a reply and will not continue until the
        reply arrives. Currently, it is up to the sender to know what type to expect back.
        """
        return await self.__inbox.send_synchronous(message)
