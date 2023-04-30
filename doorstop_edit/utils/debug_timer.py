import logging
import threading
import time
from typing import Any, Callable

logger = logging.getLogger("gui")


def time_function(msg: str) -> Callable:
    """Decorator for timing function."""

    def wrapper(func: Callable) -> Callable:
        def decorated(*args: Any, **kwargs: Any) -> Any:
            start_time = time.time()
            retval = func(*args, **kwargs)
            duration = time.time() - start_time
            logger.debug("%s took %.3f s, thread: %s", msg, duration, threading.get_native_id())
            return retval

        return decorated

    return wrapper
