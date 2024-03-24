# Core dependencies
from typing import NamedTuple

# Package dependencies
from PySide6.QtCore import SignalInstance


class Signals(NamedTuple):
    """Represents signals that are able to be emitted to alert the PySide6 GUI
    application of state transitions that should happen or other other data being
    set.
    """

    transition_to_idle: SignalInstance
    transition_to_camera_exposing: SignalInstance
    transition_to_saving_camera_images: SignalInstance
    transition_to_aborting_camera_exposure: SignalInstance
    set_exposing_time: SignalInstance
