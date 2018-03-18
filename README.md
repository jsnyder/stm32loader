STM32Loader
===========

Python script which will talk to the STM32 bootloader to upload and download firmware.

Compatible with Python version 2.6 to 2.7, 3.2 to 3.6.


Usage
-----

```
./stm32loader.py [-hqVewvr] [-l length] [-p port] [-b baud] [-a addr] [file.bin]
    -h          This help
    -q          Quiet
    -V          Verbose
    -e          Erase (note: this is required on previously written memory)
    -w          Write file content to flash
    -v          Verify flash content versus local file (recommended)
    -r          Read from flash and store in local file
    -s          Swap RTS and DTR: use RTS for reset and DTR for boot0
    -R          Make reset active high
    -B          Make boot0 active high
    -l length   Length of read
    -p port     Serial port (default: /dev/tty.usbserial-ftCYPMYJ)
    -b baud     Baud speed (default: 115200)
    -a address  Target address
    -g address  Address to start running at (0x08000000, usually)
```


Example
-------

```
stm32loader.py -e -w -v somefile.bin
```

This will pre-erase flash, write `somefile.bin` to the flash on the device, and then perform a verification after writing is finished.


Acknowledgement
---------------

Original Version by: Ivan A-R <ivan@tuxotronic.org>.

Inspiration for the configurable RTS/DTR and polarity feature:
hhttps://github.com/pazzarpj/stm32loader .

