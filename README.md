# STM32Loader

[![PyPI package](https://badge.fury.io/py/stm32loader.svg)](https://badge.fury.io/py/stm32loader)
[![GitHub Actions](https://img.shields.io/github/workflow/status/florisla/stm32loader/Test?label=tests)](https://github.com/florisla/stm32loader/actions/workflows/test.yaml)
[![GitHub Actions](https://img.shields.io/github/workflow/status/florisla/stm32loader/Lint?label=lint)](https://github.com/florisla/stm32loader/actions/workflows/lint.yaml)
[![License](https://img.shields.io/pypi/l/stm32loader.svg)](https://pypi.org/project/stm32loader/)
[![Downloads](https://pepy.tech/badge/stm32loader)](https://pepy.tech/project/stm32loader)

Python module to upload or download firmware to / from
ST Microelectronics STM32 microcontrollers over UART.

Also supports ST BlueNRG devices, and the SweetPeas bootloader
for Wiznet W7500.

Compatible with Python version 3.9 to 3.11 and PyPy 3.9.


## Installation

    pip install stm32loader

To install the latest development version:

    pip install git+https://github.com/florisla/stm32loader.git


## Usage

<!-- [[[cog
import sys
from io import StringIO
import cog
from stm32loader.main import main

sys.stdout = StringIO()

main("--help", avoid_system_exit=True)

cog.out(f"```\n{sys.stdout.getvalue()}```")

sys.stdout.close()
sys.stdout = sys.__stdout__
]]] -->
```
usage: stm32loader [-h] [-e] [-u] [-w] [-v] [-r] [-l LENGTH] -p PORT [-b BAUD] [-a ADDRESS] [-g ADDRESS] [-f FAMILY] [-V] [-q] [-s] [-R] [-B] [-n] [-P {even,none}] [--version] [FILE.BIN]

Flash firmware to STM32 microcontrollers.

positional arguments:
  FILE.BIN              File to read from or store to flash.

optional arguments:
  -h, --help            show this help message and exit
  -e, --erase           Erase (note: this is required on previously written memory).
  -u, --unprotect       Unprotect in case erase fails.
  -w, --write           Write file content to flash.
  -v, --verify          Verify flash content versus local file (recommended).
  -r, --read            Read from flash and store in local file.
  -l LENGTH, --length LENGTH
                        Length of read.
  -p PORT, --port PORT  Serial port (default: $STM32LOADER_SERIAL_PORT).
  -b BAUD, --baud BAUD  Baudrate. (default: 115200)
  -a ADDRESS, --address ADDRESS
                        Target address. (default: 134217728)
  -g ADDRESS, --go-address ADDRESS
                        Start executing from address (0x08000000, usually).
  -f FAMILY, --family FAMILY
                        Device family to read out device UID and flash size; e.g F1 for STM32F1xx (default: $STM32LOADER_FAMILY).
  -V, --verbose         Verbose mode.
  -q, --quiet           Quiet mode.
  -s, --swap-rts-dtr    Swap RTS and DTR: use RTS for reset and DTR for boot0.
  -R, --reset-active-high
                        Make RESET active high.
  -B, --boot0-active-low
                        Make BOOT0 active low.
  -n, --no-progress     Don't show progress bar.
  -P {even,none}, --parity {even,none}
                        Parity: "even" for STM32, "none" for BlueNRG. (default: even)
  --version             show program's version number and exit

examples:
  stm32loader -p COM7 -f F1
  stm32loader -e -w -v example/main.bin
```
<!-- [[[end]]] -->

## Command-line example

```
stm32loader --port /dev/tty.usbserial-ftCYPMYJ --erase --write --verify somefile.bin
```

This will pre-erase flash, write `somefile.bin` to the flash on the device, and then
perform a verification after writing is finished.

You can skip the `--port` option by configuring environment variable
`STM32LOADER_SERIAL_PORT`.
Similarly, `--family` may be supplied through `STM32LOADER_FAMILY`.

To read out firmware and store it in a file:

```
stm32loader --read --port /dev/cu.usbserial-A5XK3RJT --family F1 --length 0x10000 --address 0x08000000 dump.bin 
```


To erase the full device:

```
stm32loader --erase --port /dev/cu.usbserial-A5XK3RJT
```

Or erase only a specific region of the flash:

```
stm32loader --erase --address 0x08000000 --length 0x2000 --port /dev/cu.usbserial-A5XK3RJT
```



## Reference documents

* ST `AN2606`: STM32 microcontroller system memory boot mode
* ST `AN3155`: USART protocol used in the STM32 bootloader
* ST `AN4872`: BlueNRG-1 and BlueNRG-2 UART bootloader protocol


## Acknowledgement

Original Version by Ivan A-R (tuxotronic.org).
Contributions by Domen Puncer, James Snyder, Floris Lambrechts,
Atokulus, sam-bristow, NINI1988, Omer Kilic, Szymon Szantula, rdaforno,
Mikolaj Stawiski, Tyler Coy, Alex Klimaj, Ondrej Mikle, denniszollo,
emilzay, michsens, blueskull, Mattia Maldini, etrommer, jadeaffenjaeger,
tosmaz.

Inspiration for features from:

* Configurable RTS/DTR and polarity, extended erase with pages:
  https://github.com/pazzarpj/stm32loader
  
* Memory unprotect
  https://github.com/3drobotics/stm32loader

* Correct checksum calculation for paged erase:
  https://github.com/jsnyder/stm32loader/pull/4

* ST BlueNRG chip support
  https://github.com/lchish/stm32loader

* Wiznet W7500 chip / SweetPeas custom bootloader support
  https://github.com/Sweet-Peas/WiznetLoader


## Alternatives

If you don't need the flexibility of a Python tool, you can take
a look at other similar tools in `ALTERNATIVES.md`.


## Electrically

The below assumes you are connecting an STM32F10x.
For other chips, the serial pins and/or the BOOT0 / BOOT1 values
may differ.

Make the following connections:

- Serial adapter `GND` to MCU `GND`.
- Serial adapter power to MCU power or vice versa (either 3.3 or 5 Volt).
- Note if you're using 5 Volt signaling or 3V3 on the serial adapter.
- Serial `TX` to MCU `RX` (`PA10`).
- Serial `RX` to MCU `TX` (`PA9`).
- Serial `DTR` to MCU `RESET`.
- Serial `RTS` to MCU `BOOT0` (or `BOOT0` to 3.3V).
- MCU `BOOT1` to `GND`.

If either `RTS` or `DTR` are not available on your serial adapter, you'll have to
manually push buttons or work with jumpers.
When given a choice, set `BOOT0` manually high and drive `RESET` through the serial
adapter (it needs to toggle, whereas `BOOT0` does not).


## Not currently supported

* Command-line argument for readout protection.
* Command-line argument for write protection/unprotection.
* STM8 devices (ST `UM0560`).
* Paged flash erase for devices with page size <> 1 KiB.
* Other bootloader protocols (e.g. I2C, HEX -> implemented in `stm32flash`).


## Future work

* Use f-strings.
* Use proper logging instead of print statements.
* Start using `IntEnum` for commands and replies.
