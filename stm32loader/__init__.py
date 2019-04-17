"""Flash firmware to STM32 microcontrollers over an RS-232 serial connection."""

__version_info__ = (0, 3, 3, "dev")
__version__ = "-".join(str(part) for part in __version_info__).replace("-", ".", 2)

from .stm32loader import Stm32Loader, Stm32Bootloader, main

__all__ = ["__version_info__", "__version__", "Stm32Loader", "Stm32Bootloader", "main"]
