import json
import os


class Config:
    """Configuration Manager Class

    This class manages application configuration through a JSON file system. It provides
    functionality to load, save, and manipulate configuration settings persistently.

    Attributes:
        CONFIG_DIR (str): Absolute path to the configuration directory
        CONFIG_FILE (str): Full path to the JSON configuration file
        config (dict): Dictionary containing the current configuration settings

    Methods:
        load_config(): Loads configuration from JSON file
        save_config(): Saves current configuration to JSON file
        get(key, default=None): Retrieves a configuration value by key
        set(key, value): Sets a configuration value and saves it
        show_config(): Returns a formatted string of current configuration
    """

    CONFIG_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../data"))
    CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

    def __init__(self):
        """Loads the Json file and create the data directory if it doesn't exist"""
        os.makedirs(self.CONFIG_DIR, exist_ok=True)
        self.config = {}
        self.load_config()

    def load_config(self):
        """load a config from a json file."""
        if os.path.exists(self.CONFIG_FILE):
            with open(self.CONFIG_FILE, "r", encoding="utf-8") as f:
                self.config = json.load(f)
        else:
            self.config = {}

    def save_config(self):
        """Saves the Config file"""
        with open(self.CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=4)

    def get(self, key, default=None):
        """get the parameter"""
        return self.config.get(key, default)

    def set(self, key, value):
        """Modifie ou ajoute une valeur dans la configuration."""
        self.config[key] = value
        # saves config after writing
        self.save_config()

    def show_config(self):
        """display the config"""
        return json.dumps(self.config, indent=4)
