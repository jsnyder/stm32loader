
"""
Execute stm32loader as a module.

This does exactly the same as manually calling 'python stm32loader.py'.
"""

from .stm32loader import main as stm32loader_main


def main():
    """
    Separate main() method, different from stm32loader.main.

    This way it it can be used as an entry point for a console script.
    :return None:
    """
    stm32loader_main()


if __name__ == "__main__":
    main()
