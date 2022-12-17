import logging
import time

logger = logging.getLogger("gui")


def time_function(msg: str):
    """Decorator for timing function."""

    def wrapper(func):
        def decorated(*args, **kwargs):
            start_time = time.time()
            retval = func(*args, **kwargs)
            duration = time.time() - start_time
            logger.debug("%s took %.3f s", msg, duration)
            return retval

        return decorated

    return wrapper
