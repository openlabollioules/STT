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
    def __init__(self):
        # Création de l'instance interne du logger standard
        self._logger = logging.getLogger("Speech2Text")
        self._logger.setLevel(LOG_LEVEL_MAP.get(config.get("logger_level")))

        # Création d'un dossier pour les logs (adaptation selon votre structure)
        log_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'logs')
        os.makedirs(log_dir, exist_ok=True)

        # Handler pour la console
        console_handler = logging.StreamHandler()
        console_handler.setLevel(LOG_LEVEL_MAP.get(config.get("logger_level")))
        console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(console_formatter)

        # Handler pour les fichiers
        file_handler = logging.FileHandler(os.path.join(log_dir, "app.log"))
        file_handler.setLevel(LOG_LEVEL_MAP.get(config.get("logger_level")))
        file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)

        self._logger.addHandler(console_handler)
        self._logger.addHandler(file_handler)

    def __getattr__(self, attr):
        """
        Redirige automatiquement l'accès aux méthodes et attributs vers l'instance interne.
        Ainsi, logger.info("message") appellera self._logger.info("message").
        """
        return getattr(self._logger, attr)

logger = Logger()
