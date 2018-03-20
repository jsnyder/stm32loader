STM32Loader
===========

Python script which will talk to the STM32 bootloader to upload and download firmware.

Also supports ST BlueNRG devices, and the SweetPeas bootloader
for Wiznet W7500.

Compatible with Python version 2.6 to 2.7, 3.2 to 3.6.


Usage
-----

```
./stm32loader.py [-hqVewvr] [-l length] [-p port] [-b baud] [-a addr] [-f family] [file.bin]
    -h          This help
    -q          Quiet mode
    -V          Verbose mode
    -e          Erase (note: this is required on previously written memory)
    -w          Write file content to flash
    -v          Verify flash content versus local file (recommended)
    -r          Read from flash and store in local file
    -l length   Length of read
    -s          Swap RTS and DTR: use RTS for reset and DTR for boot0
    -R          Make reset active high
    -B          Make boot0 active high
    -P parity   Parity: "even" for STM32 (default), "none" for BlueNRG
    -p port     Serial port (default: /dev/tty.usbserial-ftCYPMYJ)
    -b baud     Baud speed (default: 115200)
    -a address  Target address
    -g address  Address to start running at (0x08000000, usually)
    -f family   Device family to read out device UID and flash size; e.g F1 for STM32F1xx
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
Contributions by Domen Puncer, James Snyder, Floris Lambrechts.

Inspiration for features from:

* Configurable RTS/DTR and polarity, extended erase with sectors:
  https://github.com/pazzarpj/stm32loader

* Correct checksum calculation for sector erase:
  https://github.com/jsnyder/stm32loader/pull/4

* ST BlueNRG chip support
  https://github.com/lchish/stm32loader

* Wiznet W7500 chip / SeetPeas custom bootloader support
  https://github.com/Sweet-Peas/WiznetLoader


Electrically
------------

The below assumes you care connecting an STM32F10x.
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
