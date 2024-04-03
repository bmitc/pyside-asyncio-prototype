"""Implements a PySide6 GUI application that contains a state machine and
talks to a core `asyncio` state machine, which the GUI application sends messages
to and responds to state transitions
"""

# Core dependencies
import asyncio
import logging
import sys
from threading import Thread

# Package dependencies
from PySide6.QtCore import Qt, Signal
from PySide6.QtStateMachine import QState, QStateMachine
from PySide6.QtWidgets import (
    QApplication,
    QLCDNumber,
    QWidget,
    QPushButton,
    QLabel,
    QHBoxLayout,
    QVBoxLayout,
)

# Project dependencies
from prototype.async_controller import AsyncController, ControllerMessage, async_controller_main
from prototype.async_core.messaging import AsyncInbox
from prototype.led_indicator import LedIndicator
from prototype.signals import Signals


class MainWindow(QWidget):
    # Create class variables that will hold the signals that will unconditionally transition
    # the GUI to the specified state
    transition_to_idle = Signal()
    transition_to_camera_exposing = Signal()
    transition_to_saving_camera_images = Signal()
    transition_to_aborting_camera_exposure = Signal()
    set_exposing_time = Signal(float)

    def __init__(self) -> None:
        super().__init__()

        # The the `asyncio` queue and event loop are created here, in the GUI thread (main thread),
        # but they will be passed into a new thread that will actually run the event loop.
        # Under no circumstances should the `AsyncInbox` be used outside of that event loop. It
        # is only okay to construct it outside of the event loop.
        self._async_inbox: AsyncInbox[ControllerMessage] = AsyncInbox[ControllerMessage](
            name="AsyncController"
        )
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
        self.signals = Signals(
            self.transition_to_idle,
            self.transition_to_camera_exposing,
            self.transition_to_saving_camera_images,
            self.transition_to_aborting_camera_exposure,
            self.set_exposing_time,
        )

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
        button_start_exposure.pressed.connect(
            lambda: self.send_controller_message(ControllerMessage.START_CAMERA_EXPOSURE)
        )
        button_stop_exposure.pressed.connect(
            lambda: self.send_controller_message(ControllerMessage.STOP_CAMERA_EXPOSURE)
        )
        button_abort_exposure.pressed.connect(
            lambda: self.send_controller_message(ControllerMessage.ABORT_CAMERA_EXPOSURE)
        )

        # Create a label, LED indicator, and LCD number indicator and add them to the right vertical layout
        label_state = QLabel()
        label_for_led_indicator = QLabel("Camera exposing?")
        led_indicator_camera_exposing = LedIndicator()
        lcd_indicator_exposing_time = QLCDNumber()
        lcd_indicator_exposing_time.setSegmentStyle(QLCDNumber.SegmentStyle.Flat)
        self.set_exposing_time.connect(
            lambda number: lcd_indicator_exposing_time.display(f"{number:.1f}")
        )

        right_column_layout.addWidget(label_state)
        right_column_layout.addWidget(
            label_for_led_indicator, alignment=Qt.AlignmentFlag.AlignHCenter
        )
        right_column_layout.addWidget(led_indicator_camera_exposing)
        right_column_layout.addWidget(lcd_indicator_exposing_time)

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
            state.addTransition(
                self.transition_to_aborting_camera_exposure, state_aborting_camera_exposure
            )

        # Configure what happens when the states are entered and set the appropriate property values
        # on various GUI elements

        # "idle" state entered
        state_idle.assignProperty(label_state, "text", "State: Idle")
        state_idle.assignProperty(led_indicator_camera_exposing, "checked", False)
        state_idle.assignProperty(button_start_exposure, "enabled", True)
        state_idle.assignProperty(button_stop_exposure, "enabled", False)
        state_idle.assignProperty(button_abort_exposure, "enabled", False)
        state_idle.assignProperty(lcd_indicator_exposing_time, "enabled", False)
        state_idle.assignProperty(lcd_indicator_exposing_time, "value", 0.0)

        # "camera_exposing" state entered
        state_camera_exposing.assignProperty(label_state, "text", "State: Camera exposing")
        state_camera_exposing.assignProperty(led_indicator_camera_exposing, "checked", True)
        state_camera_exposing.assignProperty(button_start_exposure, "enabled", False)
        state_camera_exposing.assignProperty(button_stop_exposure, "enabled", True)
        state_camera_exposing.assignProperty(button_abort_exposure, "enabled", True)
        state_idle.assignProperty(lcd_indicator_exposing_time, "enabled", True)

        # "saving_camera_images" state entered
        state_saving_camera_images.assignProperty(
            label_state, "text", "State: Saving camera images"
        )
        state_saving_camera_images.assignProperty(led_indicator_camera_exposing, "checked", False)
        state_saving_camera_images.assignProperty(button_start_exposure, "enabled", False)
        state_saving_camera_images.assignProperty(button_stop_exposure, "enabled", False)
        state_saving_camera_images.assignProperty(button_abort_exposure, "enabled", False)
        state_idle.assignProperty(lcd_indicator_exposing_time, "enabled", False)
        state_idle.assignProperty(lcd_indicator_exposing_time, "value", 0.0)

        # "aborting camera exposure" state entered
        state_aborting_camera_exposure.assignProperty(
            label_state, "text", "State: Aborting camera exposure"
        )
        state_aborting_camera_exposure.assignProperty(
            led_indicator_camera_exposing, "checked", False
        )
        state_aborting_camera_exposure.assignProperty(button_start_exposure, "enabled", False)
        state_aborting_camera_exposure.assignProperty(button_stop_exposure, "enabled", False)
        state_aborting_camera_exposure.assignProperty(button_abort_exposure, "enabled", False)
        state_idle.assignProperty(lcd_indicator_exposing_time, "enabled", False)
        state_idle.assignProperty(lcd_indicator_exposing_time, "value", 0.0)

        # Disable the user being able to resize the window by setting a fixed size
        self.setFixedWidth(500)
        self.setFixedHeight(200)

        # Start the state machine
        self.state_machine.start()

        # Show the window
        self.show()

    def send_controller_message(self, message: ControllerMessage) -> None:
        """Send the `asyncio` event loop's `AsyncInbox` a message by using the coroutine
        `send_controller_message` and sending it to run on the `asyncio` event loop, putting
        the message on the `AsyncInbox`.
        """
        asyncio.run_coroutine_threadsafe(
            coro=AsyncController.send_controller_message(inbox=self._async_inbox, message=message),
            loop=self._asyncio_event_loop,
        )


def start_asyncio_event_loop(loop: asyncio.AbstractEventLoop) -> None:
    """Starts the given `asyncio` loop on whatever the current thread is"""
    asyncio.set_event_loop(loop)
    loop.set_debug(enabled=True)
    loop.run_forever()


def run_event_loop(
    inbox: AsyncInbox[ControllerMessage], loop: asyncio.AbstractEventLoop, signals: Signals
) -> None:
    """Runs the given `asyncio` loop on a separate thread, passing the `AsyncInbox`
    to the event loop for any other thread to send messages to the event loop. The main
    coroutine that is launched on the event loop is `async_controller_main`.
    """
    thread = Thread(target=start_asyncio_event_loop, args=(loop,), daemon=True)
    thread.start()

    asyncio.run_coroutine_threadsafe(async_controller_main(inbox, signals), loop=loop)


def run_application(application: QApplication):
    application.exec()
    logging.info("Application has exited")


if __name__ == "__main__":
    logging.basicConfig(handlers=[logging.StreamHandler()], level=logging.DEBUG)
    logging.info("Started application")

    application = QApplication(sys.argv)
    window = MainWindow()
    async_inbox = window._async_inbox
    asyncio_event_loop = window._asyncio_event_loop

    run_event_loop(inbox=async_inbox, loop=asyncio_event_loop, signals=window.signals)
    sys.exit(run_application(application))
