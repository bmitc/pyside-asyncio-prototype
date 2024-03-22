# Core dependencies
import asyncio


class CameraClient:
    def __init__(self, ip_address: str, port: int) -> None:
        self.__ip_address = ip_address
        self.__port = port
        self.__reader: asyncio.StreamReader | None = None
        self.__writer: asyncio.StreamWriter | None = None

    async def __write(self, message: str) -> None:
        self.__writer.write(f"{message}\n".encode())
        await self.__writer.drain()

    async def __read(self) -> str:
        response_data: bytes = await self.__reader.readline()
        response: str = response_data.decode().strip()
        return response

    async def initialize(self) -> None:
        reader, writer = await asyncio.open_connection(self.__ip_address, self.__port)
        self.__reader = reader
        self.__writer = writer

    async def start_exposure(self) -> None:
        await self.__write("start_exposure")
        await self.__read()

    async def stop_exposure(self) -> None:
        await self.__write("stop_exposure")
        await self.__read()

    async def get_state(self) -> str:
        await self.__write("get_state")
        response = await self.__read()
        return response

    async def get_exposing_time(self) -> float:
        await self.__write("get_exposing_time")
        response = await self.__read()
        return float(response)

    async def close(self) -> None:
        self.__writer.close()
        await self.__writer.wait_closed()


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
