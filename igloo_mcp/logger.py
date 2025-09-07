import logging
import sys


LOG_FORMAT = r"[%(asctime)s | %(levelname)s | %(threadName)s | %(filename)s::%(funcName)s::%(lineno)d] "

logger = logging.getLogger("igloo_mcp")


def configure_logger(log_level: str = "INFO") -> None:
    """
    Configures the 'igloo_mcp' logger and its handlers.

    This function should be called once at application startup to ensure
    that the logging level from the configuration is applied correctly.

    Args:
        log_level (str): The minimum log level to capture (e.g., "DEBUG", "INFO").
    """
    level = logging._nameToLevel.get(log_level.upper(), logging.INFO)

    logger.setLevel(level)
    logger.propagate = False

    if logger.hasHandlers():
        logger.handlers.clear()

    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(level)

    formatter = logging.Formatter(LOG_FORMAT)
    handler.setFormatter(formatter)

    logger.addHandler(handler)
