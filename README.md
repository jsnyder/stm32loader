STM32Loader
===========

Python script which will talk to the STM32 bootloader to upload and download firmware.

Original Version by: Ivan A-R <ivan@tuxotronic.org>

## Installation

```bash
git clone git@github.com:jsnyder/stm32loader.git
cd stm32loader
pip install -r requirements.txt
```

## Usage 

```bash
./stm32loader.py [-hqVewvr] [-l length] [-p port] [-b baud] [-a addr] [file.bin]
    -h          This help
    -q          Quiet
    -V          Verbose
    -e          Erase
    -w          Write
    -v          Verify
    -r          Read
    -l length   Length of read
    -p port     Serial port (default: /dev/tty.usbserial-ftCYPMYJ)
    -b baud     Baud speed (default: 115200)
    -a addr     Target address
```

## Example

```bash
stm32loader.py -e -w -v somefile.bin
```
This will pre-erase flash, write somefile.bin to the flash on the device, and then perform a verification after writing is finished.

