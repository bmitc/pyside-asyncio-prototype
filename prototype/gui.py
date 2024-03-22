"""Implements a simple control panel for a CyberPower PDU. See the README.md for a diagram of
the state machine that is implemented here using Qt's State Machine framework.
"""

# Core dependencies
import asyncio
import sys
from threading import Thread

# Package dependencies
from PySide6.QtCore import Signal
from PySide6.QtStateMachine import QState, QStateMachine
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QPushButton,
    QLabel,
    QHBoxLayout,
    QVBoxLayout,
)

# Project dependencies
from controller import Controller, ControllerMessage, send_controller_message, Idle
from led_indicator import LedIndicator


class MainWindow(QWidget):
    # Create class variables that will hold the signals that will unconditionally transition
    # the GUI to the specified state
    transition_to_idle = Signal()
    transition_to_camera_exposing = Signal()
    transition_to_saving_camera_images = Signal()
    transition_to_aborting_camera_exposure = Signal()

    def __init__(self) -> None:
        super().__init__()

        # The the `asyncio` queue and event loop are created here, in the GUI thread (main thread),
        # but they will be passed into a new thread that will actually run the event loop.
        # Under no circumstances should the `asyncio.Queue` be used outside of that event loop. It
        # is only okay to construct it outside of the event loop.
        self._asyncio_queue = asyncio.Queue()
        self._asyncio_event_loop = asyncio.new_event_loop()

        # Create the state machine and the various states
        self.state_machine = QStateMachine(parent=self)
        self.state_idle = QState(self.state_machine)
        self.state_camera_exposing = QState(self.state_machine)
        self.state_saving_camera_images = QState(self.state_machine)
        self.state_aborting_camera_exposure = QState(self.state_machine)
        self.state_machine.setInitialState(self.state_idle)

        # Create a list of all the states so that they can be iterated through if needed
        self.states = [
            self.state_idle,
            self.state_camera_exposing,
            self.state_saving_camera_images,
            self.state_aborting_camera_exposure,
        ]

        # This is sloppy, but it can be easily replaced by a `NamedTuple` to prevent users from
        # having to index the list properly. This is just part of a quick implementation test.
        self.signals = [
            self.transition_to_idle,
            self.transition_to_camera_exposing,
            self.transition_to_saving_camera_images,
            self.transition_to_aborting_camera_exposure,
        ]

        self.initialize()

    def initialize(self) -> None:
        """Initialize the GUI widgets and state machine"""

        self.setWindowTitle("PySide with asyncio prototype")

        # Create layouts
        main_layout = QHBoxLayout()
        left_column_layout = QVBoxLayout()
        right_column_layout = QVBoxLayout()
        main_layout.addLayout(left_column_layout)
        main_layout.addLayout(right_column_layout)
        self.setLayout(main_layout)

        # Create start, stop, and abort camera exposure buttons and add them to the left
        # vertical layout
        button_start_exposure = QPushButton(text="Start exposure")
        button_stop_exposure = QPushButton(text="Stop exposure")
        button_abort_exposure = QPushButton(text="Abort exposure")

        left_column_layout.addWidget(button_start_exposure)
        left_column_layout.addWidget(button_stop_exposure)
        left_column_layout.addWidget(button_abort_exposure)

        # Add slots for sending messages to the controller when the buttons are pressed
        button_start_exposure.pressed.connect(lambda: self.send_controller_message(ControllerMessage.START_CAMERA_EXPOSURE))
        button_stop_exposure.pressed.connect(lambda: self.send_controller_message(ControllerMessage.STOP_CAMERA_EXPOSURE))
        button_abort_exposure.pressed.connect(lambda: self.send_controller_message(ControllerMessage.ABORT_CAMERA_EXPOSURE))

        # Create a label and LED indicator and add them to the right vertical layout
        label_state = QLabel()
        led_indicator_camera_exposing = LedIndicator()
        led_indicator_camera_exposing.setText("asdflkajsdf")

        right_column_layout.addWidget(label_state)
        right_column_layout.addWidget(led_indicator_camera_exposing)

        # Get the states and assign them to variables without the `self.` to make them more
        # concise to refer to

        state_idle = self.state_idle
        state_camera_exposing = self.state_camera_exposing
        state_saving_camera_images = self.state_saving_camera_images
        state_aborting_camera_exposure = self.state_aborting_camera_exposure

        # For every state, add a transition for every signal to the state that the signal describes

        for state in self.states:
            state.addTransition(self.transition_to_idle, state_idle)
            state.addTransition(self.transition_to_camera_exposing, state_camera_exposing)
            state.addTransition(self.transition_to_saving_camera_images, state_saving_camera_images)
            state.addTransition(self.transition_to_aborting_camera_exposure, state_aborting_camera_exposure)

        # Configure what happens when the states are entered and set the appropriate property values
        # on various GUI elements

        state_idle.assignProperty(label_state, "text", "Idle")
        state_idle.assignProperty(led_indicator_camera_exposing, "checked", False)
        state_idle.assignProperty(button_start_exposure, "enabled", True)
        state_idle.assignProperty(button_stop_exposure, "enabled", False)
        state_idle.assignProperty(button_abort_exposure, "enabled", False)

        state_camera_exposing.assignProperty(label_state, "text", "Camera exposing")
        state_camera_exposing.assignProperty(led_indicator_camera_exposing, "checked", True)
        state_camera_exposing.assignProperty(button_start_exposure, "enabled", False)
        state_camera_exposing.assignProperty(button_stop_exposure, "enabled", True)
        state_camera_exposing.assignProperty(button_abort_exposure, "enabled", True)

        state_saving_camera_images.assignProperty(label_state, "text", "Saving camera images")
        state_saving_camera_images.assignProperty(led_indicator_camera_exposing, "checked", False)
        state_saving_camera_images.assignProperty(button_start_exposure, "enabled", False)
        state_saving_camera_images.assignProperty(button_stop_exposure, "enabled", False)
        state_saving_camera_images.assignProperty(button_abort_exposure, "enabled", False)

        state_aborting_camera_exposure.assignProperty(label_state, "text", "Aborting camera exposure")
        state_aborting_camera_exposure.assignProperty(led_indicator_camera_exposing, "checked", False)
        state_aborting_camera_exposure.assignProperty(button_start_exposure, "enabled", False)
        state_aborting_camera_exposure.assignProperty(button_stop_exposure, "enabled", False)
        state_aborting_camera_exposure.assignProperty(button_abort_exposure, "enabled", False)

        # Disable the user being able to resize the window by setting a fixed size
        self.setFixedWidth(500)
        self.setFixedHeight(200)

        # Start the state machine
        self.state_machine.start()

        # Show the window
        self.show()

    def send_controller_message(self, message: ControllerMessage) -> None:
        """Send the `asyncio` event loop's `asyncio.Queue` a message by using the coroutine
        `send_controller_message` and sending it to run on the `asyncio` event loop, putting
        the message on the `asyncio.Queue`.
        """
        asyncio.run_coroutine_threadsafe(
            coro=send_controller_message(inbox=self._asyncio_queue, message=message),
            loop=self._asyncio_event_loop,
        )


async def read_inbox(queue: asyncio.Queue, controller: Controller):
    while True:
        message = await queue.get()
        match message:
            case ControllerMessage.START_CAMERA_EXPOSURE:
                await asyncio.to_thread(controller.start_camera_exposure)

            case ControllerMessage.STOP_CAMERA_EXPOSURE:
                await asyncio.to_thread(controller.stop_camera_exposure)

            case ControllerMessage.ABORT_CAMERA_EXPOSURE:
                await asyncio.to_thread(controller.abort_camera_exposure)


async def asyncio_main(inbox: asyncio.Queue, signals: list[Signal]):
    controller = await asyncio.to_thread(Controller, Idle(), signals)
    asyncio.gather(read_inbox(inbox, controller))


def start_asyncio_event_loop(loop: asyncio.AbstractEventLoop) -> None:
    asyncio.set_event_loop(loop)
    loop.run_forever()


def run_event_loop(inbox: asyncio.Queue, loop: asyncio.AbstractEventLoop, signals: list[Signal]) -> None:
    thread = Thread(target=start_asyncio_event_loop, args=(loop,), daemon=True)
    thread.start()

    asyncio.run_coroutine_threadsafe(asyncio_main(inbox, signals), loop=loop)


if __name__ == "__main__":
    application = QApplication(sys.argv)
    window = MainWindow()
    asyncio_queue = window._asyncio_queue
    asyncio_event_loop = window._asyncio_event_loop

    run_event_loop(inbox=asyncio_queue, loop=asyncio_event_loop, signals=window.signals)
    sys.exit(application.exec())
