import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))
from config import config


def main():
    audio_file_name = input("Entrez le nom fichier audio dans ./audiofiles: ")
    config.set("file_name", audio_file_name)


if __name__ == "__main__":
    main()
