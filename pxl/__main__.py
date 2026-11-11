import os
import sys


def run():
    # A windowed build has no stdout/stderr.
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w")
    from .webapp import main

    main()


if __name__ == "__main__":
    run()
