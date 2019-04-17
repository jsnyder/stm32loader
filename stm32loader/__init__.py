"""Flash firmware to STM32 microcontrollers over an RS-232 serial connection."""

from .__version__ import VERSION
__version__ = ".".join(map(str, VERSION))

from .stm32loader import Stm32Loader, Stm32Bootloader, main

__all__ = ["__version_info__", "__version__", "Stm32Loader", "Stm32Bootloader", "main"]
