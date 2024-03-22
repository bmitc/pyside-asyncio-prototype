# Core dependencies
import asyncio
import time
from functools import partial


class CameraServer:
    def __init__(self) -> None:
        self.__exposure_start_time: float | None = None
        self.__exposing: bool = False
        self.__idle: bool = True

    def start_exposure(self) -> None:
        self.__exposing = True
        self.__idle = False
        self.__exposure_start_time = time.time()

    def stop_exposure(self) -> None:
        self.__exposing = False
        self.__idle = True
        self.__exposure_start_time = None

    @property
    def get_exposing_time(self) -> float:
        return time.time() - self.__exposure_start_time

    @property
    def get_state(self) -> str:
        if self.__exposing:
            return "exposing"
        elif self.__idle:
            return "idle"
        else:
            return "unknown"


async def handle_echo(reader: asyncio.StreamReader, writer: asyncio.StreamWriter, camera_server: CameraServer):
    continue_listening = True

    while continue_listening:
        data = await reader.readline()
        message: str = data.decode().strip()
        addr = writer.get_extra_info("peername")

        print(f"Received {message!r} from {addr!r}")

        match message:
            case "start_exposure":
                camera_server.start_exposure()
                response = "ok"
            case "stop_exposure":
                camera_server.stop_exposure()
                response = "ok"
            case "get_exposing_time":
                response = camera_server.get_exposing_time
            case "get_state":
                response = camera_server.get_state
            case _:
                response = ""
                continue_listening = False

        writer.write(f"{response}\n".encode())
        await writer.drain()

    print("Close the connection")
    writer.close()
    await writer.wait_closed()


async def main():
    bundled = partial(handle_echo, camera_server=CameraServer())
    server = await asyncio.start_server(bundled, "127.0.0.1", 8888)

    address = ", ".join(str(sock.getsockname()) for sock in server.sockets)
    print(f"Serving on {address}")

    async with server:
        await server.serve_forever()


asyncio.run(main())
