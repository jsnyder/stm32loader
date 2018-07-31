STM32Loader
===========

Python script to upload or download firmware to / from
ST Microelectronics STM32 microcontrollers over UART.

Also supports ST BlueNRG devices, and the SweetPeas bootloader
for Wiznet W7500.

Compatible with Python version 3.2 to 3.7 or 2.7.


Usage
-----

```
./stm32loader.py [-hqVewvrsRB] [-l length] [-p port] [-b baud] [-P parity] [-a address] [-g address] [-f family] [file.bin]
    -e          Erase (note: this is required on previously written memory)
    -u          Readout unprotect
    -w          Write file content to flash
    -v          Verify flash content versus local file (recommended)
    -r          Read from flash and store in local file
    -l length   Length of read
    -p port     Serial port (default: /dev/tty.usbserial-ftCYPMYJ)
    -b baud     Baud speed (default: 115200)
    -a address  Target address (default: 0x08000000)
    -g address  Start executing from address (0x08000000, usually)
    -f family   Device family to read out device UID and flash size; e.g F1 for STM32F1xx

    -h          Print this help text
    -q          Quiet mode
    -V          Verbose mode

    -s          Swap RTS and DTR: use RTS for reset and DTR for boot0
    -R          Make reset active high
    -B          Make boot0 active high
    -u          Readout unprotect
    -P parity   Parity: "even" for STM32 (default), "none" for BlueNRG
```


Example
-------

```
stm32loader.py -e -w -v somefile.bin
```

This will pre-erase flash, write `somefile.bin` to the flash on the device, and then perform a verification after writing is finished.


Reference documents
-------------------

* ST AN2606: STM32 microcontroller system memory boot mode
* ST AN3155: USART protocol used in the STM32 bootloader
* ST AN4872: BlueNRG-1 and BlueNRG-2 UART bootloader protocol


Acknowledgement
---------------

Original Version by Ivan A-R (tuxotronic.org).
Contributions by Domen Puncer, James Snyder, Floris Lambrechts,
Atokulus.

Inspiration for features from:

* Configurable RTS/DTR and polarity, extended erase with sectors:
  https://github.com/pazzarpj/stm32loader
  
* Memory unprotect
  https://github.com/3drobotics/stm32loader

* Correct checksum calculation for sector erase:
  https://github.com/jsnyder/stm32loader/pull/4

* ST BlueNRG chip support
  https://github.com/lchish/stm32loader

* Wiznet W7500 chip / SweetPeas custom bootloader support
  https://github.com/Sweet-Peas/WiznetLoader


Electrically
------------

The below assumes you are connecting an STM32F10x.
For other chips, the serial pins and/or the BOOT0 / BOOT1 values
may differ.

Make the following connections:

- Serial adapter GND to MCU GND.
- Serial adapter power to MCU power or vice versa (either 3.3 or 5 Volt).
- Note if you're using 5 Volt signaling or 3V3 on the serial adapter.
- Serial TX to MCU RX (PA10).
- Serial RX to MCU TX (PA9).
- Serial DTR to MCU RESET.
- Serial RTS to MCU BOOT0 (or BOOT0 to 3.3V).
- MCU BOOT1 to GND.

If either RTS or DTR are not available on your serial adapter, you'll have to
manually push buttons or work with jumpers.
When given a choice, set BOOT0 manually high and drive reset through the serial
adepter (it needs to toggle, whereas BOOT0 does not).


Not currently supported
-----------------------

* Extended erase with specific sectors
* Command-line argument for readout protection
* Command-line argument for write protection/unprotection
* STM8 devices (ST UM0560)
* Other bootloader protocols (e.g. I2C, HEX -> implemented in stm32flash)
