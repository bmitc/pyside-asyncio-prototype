# Core dependencies
from abc import ABC, abstractmethod
import logging
from typing import final


class AsyncLoggingMixin(ABC):
    @abstractmethod
    def _async_log_name(self) -> str:
        """The logging name that the concrete implementation should override. The name
        is used in the logging message as`<_async_log_name>: <log_message>`.
        """
        ...

    @final
    def _async_log_debug(self, log_message: str) -> None:
        """Logs to the "asyncio" logger, which is required for when logging from a
        coroutine. Uses the required override of `_async_log_name` to create a log
        message of the form `<_async_log_name>: <log_message>`.
        """
        logging.getLogger("asyncio").debug(f"{self._async_log_name()}: {log_message}")
