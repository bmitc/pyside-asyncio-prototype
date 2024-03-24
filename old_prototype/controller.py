# Core dependencies
# The `__future__` import must be listed first. Otherwise, a `SyntaxError` is emitted.
from __future__ import annotations
from abc import ABC, abstractmethod
import asyncio
from enum import Enum, auto
from typing import override

# Package dependencies
from PySide6.QtCore import Signal


class Controller:
    def __init__(self, initial_state: IState, signals: list[Signal]) -> None:
        """Initialize the controller to the given initial state and call the `
        on_entry` method for the state.
        """
        self.__signals = signals
        self.__state = initial_state
        self.__state.controller = self
        self.__state.signals = signals
        self.__state.on_entry()

    def _transition_to(self, new_state: IState) -> None:
        """Transition from the current state to the given new state. This calls
        the `on_exit` method on the current state and the `on_entry` of the
        new state. This method should not be called by any object other than
        concrete implementations of `IState`.
        """
        self.__state.on_exit()
        self.__state = new_state
        self.__state.controller = self
        self.__state.signals = self.__signals
        self.__state.on_entry()

    @property
    def state(self):
        """Get the current state"""
        return self.__state

    def start_camera_exposure(self) -> None:
        self.__state.start_camera_exposure()

    def stop_camera_exposure(self) -> None:
        self.__state.stop_camera_exposure()

    def abort_camera_exposure(self) -> None:
        self.__state.abort_camera_exposure()


class IState(ABC):
    """Serve as an interface between the controller and the explicit, individual states."""

    @property
    def controller(self) -> Controller:
        return self.__controller

    @controller.setter
    def controller(self, controller: Controller) -> None:
        self.__controller = controller

    @property
    def signals(self) -> list[Signal]:
        return self.__signals

    @signals.setter
    def signals(self, signals: list[Signal]):
        self.__signals = signals

    def on_entry(self) -> None:
        """Can be overridden by a state to perform an action when the state is
        being entered, i.e., transitions into. It is not required to be overridden.
        """
        pass

    def on_exit(self) -> None:
        """Can be overridden by a state to perform an action when the state is
        being exited, i.e., transitioned from. It is not required to be overridden.
        """
        pass

    # If a concrete implementation does not handle the called method, i.e., it is an invalid action
    # in the specific state, it is enough to simply call `pass`.

    @abstractmethod
    def start_camera_exposure(self) -> None: ...

    @abstractmethod
    def stop_camera_exposure(self) -> None: ...

    @abstractmethod
    def abort_camera_exposure(self) -> None: ...


class Idle(IState):
    @override
    def on_entry(self):
        self.signals[0].emit()
        print("Idling ...")

    def start_camera_exposure(self) -> None:
        self.controller._transition_to(CameraExposing())

    def stop_camera_exposure(self) -> None:
        pass

    def abort_camera_exposure(self) -> None:
        pass


class CameraExposing(IState):
    @override
    def on_entry(self) -> None:
        self.signals[1].emit()
        print("Starting camera exposure ...")

    @override
    def on_exit(self) -> None:
        print("Stopping camera exposure ...")

    def start_camera_exposure(self) -> None:
        pass

    def stop_camera_exposure(self) -> None:
        self.controller._transition_to(SavingCameraImages())

    def abort_camera_exposure(self) -> None:
        self.controller._transition_to(AbortingCameraExposure())


class SavingCameraImages(IState):
    @override
    def on_entry(self) -> None:
        self.signals[2].emit()
        print("Saving camera images ...")
        self.controller._transition_to(Idle())

    def start_camera_exposure(self) -> None:
        pass

    def stop_camera_exposure(self) -> None:
        pass

    def abort_camera_exposure(self) -> None:
        pass


class AbortingCameraExposure(IState):
    @override
    def on_entry(self) -> None:
        self.signals[3].emit()
        print("Aborting camera exposure ...")
        self.controller._transition_to(Idle())

    def start_camera_exposure(self) -> None:
        pass

    def stop_camera_exposure(self) -> None:
        pass

    def abort_camera_exposure(self) -> None:
        pass


if __name__ == "__main__":
    controller = Controller(Idle())
    controller.start_camera_exposure()
    controller.stop_camera_exposure()


class ControllerMessage(Enum):
    START_CAMERA_EXPOSURE = auto()
    STOP_CAMERA_EXPOSURE = auto()
    ABORT_CAMERA_EXPOSURE = auto()


async def send_controller_message(inbox: asyncio.Queue, message: ControllerMessage):
    inbox.put_nowait(message)


async def read_controller_inbox(inbox: asyncio.Queue, controller: Controller):
    message = await inbox.get()

    match message:
        case ControllerMessage.START_CAMERA_EXPOSURE:
            controller.start_camera_exposure()

        case ControllerMessage.STOP_CAMERA_EXPOSURE:
            controller.stop_camera_exposure()

        case ControllerMessage.ABORT_CAMERA_EXPOSURE:
            controller.abort_camera_exposure()
