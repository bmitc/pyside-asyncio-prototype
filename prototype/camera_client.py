# Core dependencies
import asyncio

# Project dependencies
from prototype.async_client_mixins import AsyncTCPClientMixin


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


async def main():
    camera_client = CameraClient("127.0.0.1", 8888)
    await camera_client.initialize()
    print(f"State: {await camera_client.get_state()}")
    await camera_client.start_exposure()
    print(f"State: {await camera_client.get_state()}")
    await asyncio.sleep(2)
    print(f"Exposing time: {await camera_client.get_exposing_time()}")
    await asyncio.sleep(5)
    print(f"Exposing time: {await camera_client.get_exposing_time()}")
    await camera_client.stop_exposure()
    print(f"State: {await camera_client.get_state()}")
    await camera_client.close()


if __name__ == "__main__":
    asyncio.run(main())
