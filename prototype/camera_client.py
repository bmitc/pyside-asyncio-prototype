# Core dependencies
from typing import final

# Project dependencies
from prototype.async_client_mixins import AsyncTCPClientMixin


@final
class CameraClient(AsyncTCPClientMixin):
    def __init__(self, ip_address: str, port: int) -> None:
        super().__init__(ip_address, port)

    async def start_exposure(self) -> None:
        await self._write("start_exposure")
        await self._read()

    async def stop_exposure(self) -> None:
        await self._write("stop_exposure")
        await self._read()

    async def get_state(self) -> str:
        await self._write("get_state")
        response = await self._read()
        return response

    async def get_exposing_time(self) -> float:
        await self._write("get_exposing_time")
        response = await self._read()
        return float(response)
