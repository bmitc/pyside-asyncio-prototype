# Core dependencies
from enum import Enum, auto
from typing import final, override

# Project dependencies
from prototype.async_core.messaging import ReplyChannel
from prototype.async_core.worker import AsyncWorker
from prototype.async_clients.camera_client import CameraClient


class CameraMessage(Enum):
    """Represents a message that can be sent to an `AsyncCameraWorker`"""

    START_EXPOSURE = auto()
    STOP_EXPOSURE = auto()


@final
class AsyncCameraWorker(AsyncWorker[CameraMessage]):
    def __init__(self, ip_address: str, port: int) -> None:
        super().__init__(name="AsyncCameraWorker")
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

    @override
    async def _receive_synchronous_message(self, message: CameraMessage, reply_channel: ReplyChannel) -> None:
        pass
