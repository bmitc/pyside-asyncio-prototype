# Core dependencies
# The `__future__` import must be listed first. Otherwise, a `SyntaxError` is emitted.
from __future__ import annotations
from abc import ABC, abstractmethod
import asyncio
from enum import Enum, auto, verify, UNIQUE
from typing import override

# Package dependencies
from PySide6.QtCore import Signal

# Project dependencies
from prototype.camera_client import CameraClient


class AsyncController:
    def __init__(self, initial_state: IState, signals: list[Signal]) -> None:
        """Initialize the controller to the given initial state and call the `
        on_entry` method for the state.
        """
        self.__state = initial_state
        self.__signals = signals
        self.__camera_client = CameraClient("127.0.0.1", 8888)

        # Set initial state properties
        self.__state.controller = self
        self.__state.signals = signals
        self.__state.camera_client = self.__camera_client

    async def initialize(self) -> None:
        await self.__camera_client.initialize()
        await self.__state.on_entry()

    async def _transition_to(self, new_state: IState) -> None:
        """Transition from the current state to the given new state. This calls
        the `on_exit` method on the current state and the `on_entry` of the
        new state. This method should not be called by any object other than
        concrete implementations of `IState`.
        """
        await self.__state.on_exit()
        self.__state = new_state
        self.__state.controller = self
        self.__state.signals = self.__signals
        self.__state.camera_client = self.__camera_client
        await self.__state.on_entry()

    @property
    def state(self):
        """Get the current state"""
        return self.__state

    @staticmethod
    async def send_controller_message(inbox: asyncio.Queue, message: ControllerMessage):
        inbox.put_nowait(message)

    # Messages that the controller can be "sent" by calling methods on it.
    # The messages are then deferred down to the specific state that the
    # controller is in.

    async def start_camera_exposure(self) -> None:
        await self.__state.start_camera_exposure()

    async def stop_camera_exposure(self) -> None:
        await self.__state.stop_camera_exposure()

    async def abort_camera_exposure(self) -> None:
        await self.__state.abort_camera_exposure()

    async def get_exposing_time(self) -> float:
        exposing_time = await self.__state.get_exposing_time()
        self.__signals[4].emit(exposing_time)
        return exposing_time


class IState(ABC):
    """Serve as an interface between the controller and the explicit, individual states."""

    @property
    def controller(self) -> AsyncController:
        return self.__controller

    @controller.setter
    def controller(self, controller: AsyncController) -> None:
        self.__controller = controller

    @property
    def signals(self) -> list[Signal]:
        return self.__signals

    @signals.setter
    def signals(self, signals: list[Signal]):
        self.__signals = signals

    @property
    def camera_client(self) -> CameraClient:
        return self.__camera_client

    @camera_client.setter
    def camera_client(self, camera_client: CameraClient):
        self.__camera_client = camera_client

    async def on_entry(self) -> None:
        """Can be overridden by a state to perform an action when the state is
        being entered, i.e., transitions into. It is not required to be overridden.
        """
        pass

    async def on_exit(self) -> None:
        """Can be overridden by a state to perform an action when the state is
        being exited, i.e., transitioned from. It is not required to be overridden.
        """
        pass

    # If a concrete implementation does not handle the called method, i.e., it is an invalid action
    # in the specific state, it is enough to simply call `pass`.

    @abstractmethod
    async def start_camera_exposure(self) -> None: ...

    @abstractmethod
    async def stop_camera_exposure(self) -> None: ...

    @abstractmethod
    async def abort_camera_exposure(self) -> None: ...

    @abstractmethod
    async def get_exposing_time(self) -> float: ...


class Idle(IState):
    @override
    async def on_entry(self):
        self.signals[0].emit()
        print("Idling ...")

    async def start_camera_exposure(self) -> None:
        await self.controller._transition_to(CameraExposing())

    async def stop_camera_exposure(self) -> None:
        pass

    async def abort_camera_exposure(self) -> None:
        pass

    async def get_exposing_time(self) -> float:
        return 0.0


class CameraExposing(IState):
    @override
    async def on_entry(self) -> None:
        self.signals[1].emit()
        print("Starting camera exposure ...")
        await self.camera_client.start_exposure()

    @override
    async def on_exit(self) -> None:
        print("Stopping camera exposure ...")
        await self.camera_client.stop_exposure()

    async def start_camera_exposure(self) -> None:
        pass

    async def stop_camera_exposure(self) -> None:
        await self.controller._transition_to(SavingCameraImages())

    async def abort_camera_exposure(self) -> None:
        await self.controller._transition_to(AbortingCameraExposure())

    async def get_exposing_time(self) -> float:
        return await self.camera_client.get_exposing_time()


class SavingCameraImages(IState):
    @override
    async def on_entry(self) -> None:
        self.signals[2].emit()
        print("Saving camera images ...")

        # Simulate saving images by sleeping 2 seconds
        await asyncio.sleep(2)

        await self.controller._transition_to(Idle())

    async def start_camera_exposure(self) -> None:
        pass

    async def stop_camera_exposure(self) -> None:
        pass

    async def abort_camera_exposure(self) -> None:
        pass

    async def get_exposing_time(self) -> float:
        return 0.0


class AbortingCameraExposure(IState):
    @override
    async def on_entry(self) -> None:
        self.signals[3].emit()
        print("Aborting camera exposure ...")

        # Simulate throwing away images and other tasks by sleeping 2 seconds
        await asyncio.sleep(2)

        await self.controller._transition_to(Idle())

    async def start_camera_exposure(self) -> None:
        pass

    async def stop_camera_exposure(self) -> None:
        pass

    async def abort_camera_exposure(self) -> None:
        pass

    async def get_exposing_time(self) -> float:
        return 0.0


@verify(UNIQUE)
class ControllerMessage(Enum):
    START_CAMERA_EXPOSURE = auto()
    STOP_CAMERA_EXPOSURE = auto()
    ABORT_CAMERA_EXPOSURE = auto()
    GET_EXPOSING_TIME = auto()


async def read_inbox(queue: asyncio.Queue, controller: AsyncController):
    while True:
        message = await queue.get()
        match message:
            case ControllerMessage.START_CAMERA_EXPOSURE:
                await controller.start_camera_exposure()

            case ControllerMessage.STOP_CAMERA_EXPOSURE:
                await controller.stop_camera_exposure()

            case ControllerMessage.ABORT_CAMERA_EXPOSURE:
                await controller.abort_camera_exposure()

            case ControllerMessage.GET_EXPOSING_TIME:
                await controller.get_exposing_time()


async def periodically_get_status(inbox: asyncio.Queue, controller: AsyncController):
    while True:
        await inbox.put(ControllerMessage.GET_EXPOSING_TIME)
        await asyncio.sleep(0.1)


async def async_controller_main(inbox: asyncio.Queue, signals: list[Signal]):
    controller = AsyncController(initial_state=Idle(), signals=signals)
    await controller.initialize()
    asyncio.gather(read_inbox(inbox, controller), periodically_get_status(inbox, controller))
