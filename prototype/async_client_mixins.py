# Core dependencies
import asyncio


class AsyncTCPClientMixin:
    def __init__(self, ip_address: str, port: int) -> None:
        self.__ip_address = ip_address
        self.__port = port
        self.__reader: asyncio.StreamReader | None = None
        self.__writer: asyncio.StreamWriter | None = None

    async def _write(self, message: str) -> None:
        self.__writer.write(f"{message}\n".encode())
        await self.__writer.drain()

    async def _read(self) -> str:
        response_data: bytes = await self.__reader.readline()
        response: str = response_data.decode().strip()
        return response

    async def initialize(self) -> None:
        reader, writer = await asyncio.open_connection(self.__ip_address, self.__port)
        self.__reader = reader
        self.__writer = writer
        await self._specialized_initialize()

    async def _specialized_initialize(self) -> None:
        pass

    async def close(self) -> None:
        await self._specialized_close()
        self.__writer.close()
        await self.__writer.wait_closed()

    async def _specialized_close(self) -> None:
        pass
