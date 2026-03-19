"""Allow running as `python3 -m aicodezh`."""

import sys

if __name__ == "__main__":
    from aicodezh.cli import run
    run()
