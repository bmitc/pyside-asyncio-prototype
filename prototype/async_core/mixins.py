"""A collection of mixin classes to make building asynchronous clients
and workers easier
"""

# Core dependencies
from abc import ABC, abstractmethod
import asyncio
import logging
from typing import final


class AsyncLoggingMixin(ABC):
    """A mixin to provide easy `asyncio` logging. Simply override the `_async_log_name` and
    then call the `_async_log_debug` method to use.
    """

    @abstractmethod
    def async_log_name(self) -> str:
        """The logging name that the concrete implementation should override. The name
        is used in the logging message as`<_async_log_name>: <log_message>`.
        """
        ...

    @final
    def async_log_debug(self, log_message: str) -> None:
        """Logs to the "asyncio" logger, which is required for when logging from a
        coroutine. Uses the required override of `_async_log_name` to create a log
        message of the form `<_async_log_name>: <log_message>`.
        """
        logging.getLogger("asyncio").debug(f"{self.async_log_name()}: {log_message}")


class AsyncTCPClientMixin(ABC):
    """A mixin to add into a class to get `asyncio` streams behavior, allowing easy
    TCP reads and writes. A class adding this mixin has the option of overriding the
    `_specialized_initialize` and `_specialized_shutdown` methods if they need that
    behavior.

    A concrete user of this mixin should call this mixin's `__init__` method and use
    the `_write` and `_read` methods to make TCP/IP writes and reads, respectively.
    """

    def __init__(self, ip_address: str, port: int) -> None:
        self.__ip_address = ip_address
        self.__port = port
        self.__reader: asyncio.StreamReader
        self.__writer: asyncio.StreamWriter

    @final
    async def _write(self, message: str) -> None:
        """Write the message by appending a newline "\n" character at the end. This method
        is only intended to be called by a concrete implementation of this class."""
        self.__writer.write(f"{message}\n".encode())
        await self.__writer.drain()

    @final
    async def _read(self) -> str:
        """Reads a line by waiting for a newline "\n" character. The newline character
        is not returned in the response string. In fact, all whitespace is trimmed from
        both the beginning and end of the response string. This method is only intended
        to be called by a concrete implementation of this class.
        """
        response_data: bytes = await self.__reader.readline()
        # Decode and strip any whitespace from the response string
        response: str = response_data.decode().strip()
        return response

    @final
    async def initialize(self) -> None:
        """Initializes the `asyncio` streams reader and writer used in the `_read` and
        `_write` methods, respectively. This method is final and thus cannot be overridden.
        If a concrete implementation needs specialized initialization, then override the
        `_specialized_initialize` method.
        """
        reader, writer = await asyncio.open_connection(self.__ip_address, self.__port)
        self.__reader = reader
        self.__writer = writer
        await self._specialized_initialize()

    @final
    async def close(self) -> None:
        """Closes the `asyncio` stream connection. This method is final and thus cannot be
        overridden. If a concrete implementation needs specialized initialization, then
        override the `_specialized_close` method."""
        await self._specialized_close()
        self.__writer.close()
        await self.__writer.wait_closed()

    async def _specialized_initialize(self) -> None:
        """An optional override for a concrete implementation to provide any specialized
        initialization. This is called *after* the `initialize` method and thus after any
        of the `asyncio` streams connection, reader, and writer are initialized."""
        pass

    async def _specialized_close(self) -> None:
        """An optional override for a concrete implementation to provide any specialized
        close behavior. This is called *before* the `close` method and thus before any
        of the `asyncio` streams connection, reader, and writer are closed."""
        pass
