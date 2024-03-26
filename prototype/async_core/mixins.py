# Core dependencies
from abc import ABC, abstractmethod
import asyncio
import logging
from typing import final


class AsyncLoggingMixin(ABC):
    @abstractmethod
    def _async_log_name(self) -> str:
        """The logging name that the concrete implementation should override. The name
        is used in the logging message as`<_async_log_name>: <log_message>`.
        """
        ...

    @final
    def _async_log_debug(self, log_message: str) -> None:
        """Logs to the "asyncio" logger, which is required for when logging from a
        coroutine. Uses the required override of `_async_log_name` to create a log
        message of the form `<_async_log_name>: <log_message>`.
        """
        logging.getLogger("asyncio").debug(f"{self._async_log_name()}: {log_message}")


class AsyncTCPClientMixin:
    """A mixin to add into a class to get `asyncio` streams behavior, allowing easy
    TCP reads and writes. A class adding this mixin has the option of overriding the
    `_specialized_initialize` and `_specialized_shutdown` methods if they need that
    behavior.
    """

    def __init__(self, ip_address: str, port: int) -> None:
        self.__ip_address = ip_address
        self.__port = port
        self.__reader: asyncio.StreamReader
        self.__writer: asyncio.StreamWriter

    @final
    async def _write(self, message: str) -> None:
        self.__writer.write(f"{message}\n".encode())
        await self.__writer.drain()

    @final
    async def _read(self) -> str:
        response_data: bytes = await self.__reader.readline()
        response: str = response_data.decode().strip()
        return response

    @final
    async def initialize(self) -> None:
        reader, writer = await asyncio.open_connection(self.__ip_address, self.__port)
        self.__reader = reader
        self.__writer = writer
        await self._specialized_initialize()

    @final
    async def close(self) -> None:
        await self._specialized_close()
        self.__writer.close()
        await self.__writer.wait_closed()

    async def _specialized_initialize(self) -> None:
        pass

    async def _specialized_close(self) -> None:
        pass
