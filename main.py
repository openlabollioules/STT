import os, sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))
from frontend import run

if __name__ == "__main__":
    run()