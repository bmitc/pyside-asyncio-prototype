# Core dependencies
import asyncio
from enum import Enum, auto

# Project dependencies
from prototype.async_worker import AsyncWorker
from prototype.camera_client import CameraClient


class CameraMessage(Enum):
    START_EXPOSURE = auto()
    STOP_EXPOSURE = auto()


class AsyncCameraWorker(AsyncWorker[CameraMessage]):
    def __init__(self) -> None:
        self.__camera_client = CameraClient("127.0.0.1", 8888)

    async def _initialize(self) -> None:
        await self.__camera_client.initialize()

    async def _shutdown(self) -> None:
        await self.__camera_client.close()

    async def _receive_message(self, message: CameraMessage) -> None:
        match message:
            case CameraMessage.START_EXPOSURE:
                await self.__camera_client.start_exposure()
            case CameraMessage.STOP_EXPOSURE:
                await self.__camera_client.stop_exposure()
