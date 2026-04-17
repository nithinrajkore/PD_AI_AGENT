"""Module entrypoint for `python -m pd_agent`."""

from pd_agent import __version__


def main() -> None:
    print(f"pd_agent {__version__}")


if __name__ == "__main__":
    main()
