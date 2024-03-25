# Core dependencies
from enum import Enum, auto
from typing import override, final

# Package dependencies
from prototype.async_worker import AsyncWorker
from prototype.camera_client import CameraClient


class CameraMessage(Enum):
    START_EXPOSURE = auto()
    STOP_EXPOSURE = auto()


@final
class AsyncCameraWorker(AsyncWorker[CameraMessage]):
    def __init__(self, ip_address: str, port: int) -> None:
        self.__camera_client = CameraClient(ip_address, port)

    @override
    async def _initialize(self) -> None:
        await self.__camera_client.initialize()

    @override
    async def _shutdown(self) -> None:
        await self.__camera_client.close()

    @override
    async def _receive_message(self, message: CameraMessage) -> None:
        match message:
            case CameraMessage.START_EXPOSURE:
                await self.__camera_client.start_exposure()
            case CameraMessage.STOP_EXPOSURE:
                await self.__camera_client.stop_exposure()
