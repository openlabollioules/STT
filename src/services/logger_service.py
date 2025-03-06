import logging
import os,sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from config import config

LOG_LEVEL_MAP = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL
}

class Logger:
    """Logger class for Speech2Text application.

    This class provides a wrapper around the standard Python logging module,
    implementing both console and file logging with customizable log levels.
    The logger creates log files in a 'logs' directory and outputs formatted
    messages to both console and file.

    Attributes:
        _logger (logging.Logger): Internal logger instance named "Speech2Text"

    Methods:
        __getattr__(attr): Allows direct access to internal logger methods
            through attribute delegation

    Usage:
        logger = Logger()
        logger.info("Info message")
        logger.error("Error message")
        logger.debug("Debug message")

    Note:
        Log level is configured through the application's config using "logger_level"
        Logs are stored in the 'logs' directory under 'app.log'
        Console output format: "timestamp - level - message"
        File output format: "timestamp - logger_name - level - message"
    """
    def __init__(self):
        # init logger instance
        self._logger = logging.getLogger("Speech2Text")
        self._logger.setLevel(LOG_LEVEL_MAP.get(config.get("logger_level")))

        # Creating  a logs directory if it doesn't exist
        log_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'logs')
        os.makedirs(log_dir, exist_ok=True)

        # handler for the console
        console_handler = logging.StreamHandler()
        console_handler.setLevel(LOG_LEVEL_MAP.get(config.get("logger_level")))
        console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(console_formatter)

        # Handler for files
        file_handler = logging.FileHandler(os.path.join(log_dir, "app.log"))
        file_handler.setLevel(LOG_LEVEL_MAP.get(config.get("logger_level")))
        file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)

        self._logger.addHandler(console_handler)
        self._logger.addHandler(file_handler)

    def __getattr__(self, attr):
        """
        Redirects access to methods and attributes to the internal instance.
        This way, logger.info("message") will call self._logger.info("message").
        """
        return getattr(self._logger, attr)

logger = Logger()
