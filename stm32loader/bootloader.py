# Authors: Ivan A-R, Floris Lambrechts
# GitHub repository: https://github.com/florisla/stm32loader
#
# This file is part of stm32loader.
#
# stm32loader is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation; either version 3, or (at your option) any later
# version.
#
# stm32loader is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
# or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.
#
# You should have received a copy of the GNU General Public License
# along with stm32loader; see the file LICENSE.  If not see
# <http://www.gnu.org/licenses/>.

"""Talk to an STM32 native bootloader (see ST AN3155)."""


import math
import operator
import struct
import sys
import time
from functools import reduce

CHIP_IDS = {
    # see ST AN2606 Table 136 Bootloader device-dependent parameters
    # 16 to 32 KiB
    0x412: "STM32F10x Low-density",
    0x444: "STM32F03xx4/6",
    # 64 to 128 KiB
    0x410: "STM32F10x Medium-density",
    0x420: "STM32F10x Medium-density value line",
    0x460: "STM32G0x1",
    # 256 to 512 KiB (5128 Kbyte is probably a typo?)
    0x414: "STM32F10x High-density",
    0x428: "STM32F10x High-density value line",
    # 768 to 1024 KiB
    0x430: "STM3210xx XL-density",
    # flash size to be looked up
    0x417: "STM32L05xxx/06xxx",
    0x416: "STM32L1xxx6(8/B) Medium-density ultralow power line",
    0x411: "STM32F2xxx",
    0x433: "STM32F4xxD/E",
    # STM32F3
    0x432: "STM32F373xx/378xx",
    0x422: "STM32F302xB(C)/303xB(C)/358xx",
    0x439: "STM32F301xx/302x4(6/8)/318xx",
    0x438: "STM32F303x4(6/8)/334xx/328xx",
    0x446: "STM32F302xD(E)/303xD(E)/398xx",
    # RM0090 in ( 38.6.1 MCU device ID code )
    0x413: "STM32F405xx/07xx and STM32F415xx/17xx",
    0x419: "STM32F42xxx and STM32F43xxx",
    0x449: "STM32F74xxx/75xxx",
    0x450: "STM32H76xxx/77xxx",
    0x451: "STM32F76xxx/77xxx",
    # RM0394 46.6.1 MCU device ID code
    0x435: "STM32L4xx",
    # see ST AN4872
    # requires parity None
    0x11103: "BlueNRG",
    # STM32F0 RM0091 Table 136. DEV_ID and REV_ID field values
    0x440: "STM32F030x8",
    0x445: "STM32F070x6",
    0x448: "STM32F070xB",
    0x442: "STM32F030xC",
    # Cortex-M0 MCU with hardware TCP/IP and MAC
    # (SweetPeas custom bootloader)
    0x801: "Wiznet W7500",
    0x457: "STM32L01xxx/02xxx"
}


class Stm32LoaderError(Exception):
    """Generic exception type for errors occurring in stm32loader."""


class CommandError(Stm32LoaderError, IOError):
    """Exception: a command in the STM32 native bootloader failed."""


class PageIndexError(Stm32LoaderError, ValueError):
    """Exception: invalid page index given."""


class DataLengthError(Stm32LoaderError, ValueError):
    """Exception: invalid data length given."""


class DataMismatchError(Stm32LoaderError):
    """Exception: data comparison failed."""


class ShowProgress:
    """
    Show progress through a progress bar, as a context manager.

    Return the progress bar object on context enter, allowing the
    caller to to call next().

    Allow to supply the desired progress bar as None, to disable
    progress bar output.
    """

    class _NoProgressBar:
        """
        Stub to replace a real progress.bar.Bar.

        Use this if you don't want progress bar output, or if
        there's an ImportError of progress module.
        """

        def next(self):  # noqa
            """Do nothing; be compatible to progress.bar.Bar."""

        def finish(self):
            """Do nothing; be compatible to progress.bar.Bar."""

    def __init__(self, progress_bar_type):
        """
        Construct the context manager object.

        :param progress_bar_type type: Type of progress bar to use.
           Set to None if you don't want progress bar output.
        """
        self.progress_bar_type = progress_bar_type
        self.progress_bar = None

    def __call__(self, message, maximum):
        """
        Return a context manager for a progress bar.

        :param str message: Message to show next to the progress bar.
        :param int maximum: Maximum value of the progress bar (value at 100%).
          E.g. 256.
        :return ShowProgress: Context manager object.
        """
        if not self.progress_bar_type:
            self.progress_bar = self._NoProgressBar()
        else:
            self.progress_bar = self.progress_bar_type(
                message, max=maximum, suffix="%(index)d/%(max)d"
            )

        return self

    def __enter__(self):
        """Enter context: return progress bar to allow calling next()."""
        return self.progress_bar

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context: clean up by finish()ing the progress bar."""
        self.progress_bar.finish()


class Stm32Bootloader:
    """Talk to the STM32 native bootloader."""

    # pylint: disable=too-many-public-methods

    class Command:
        """STM32 native bootloader command values."""

        # pylint: disable=too-few-public-methods
        # FIXME turn into intenum

        # See ST AN3155, AN4872
        GET = 0x00
        GET_VERSION = 0x01
        GET_ID = 0x02
        READ_MEMORY = 0x11
        GO = 0x21
        WRITE_MEMORY = 0x31
        ERASE = 0x43
        READOUT_PROTECT = 0x82
        READOUT_UNPROTECT = 0x92
        # these not supported on BlueNRG
        EXTENDED_ERASE = 0x44
        WRITE_PROTECT = 0x63
        WRITE_UNPROTECT = 0x73

        # not used so far
        READOUT_PROTECT = 0x82
        READOUT_UNPROTECT = 0x92

        # not really listed under commands, but still...
        # 'wake the bootloader' == 'activate USART' == 'synchronize'
        SYNCHRONIZE = 0x7F

    class Reply:
        """STM32 native bootloader reply status codes."""

        # pylint: disable=too-few-public-methods
        # FIXME turn into intenum

        # See ST AN3155, AN4872
        ACK = 0x79
        NACK = 0x1F

    UID_ADDRESS = {
        # No unique id for these parts
        "F0": None,
        # ST RM0008 section 30.1 Unique device ID register
        # F101, F102, F103, F105, F107
        "F1": 0x1FFFF7E8,
        # ST RM0366 section 29.1 Unique device ID register
        # ST RM0365 section 34.1 Unique device ID register
        # ST RM0316 section 34.1 Unique device ID register
        # ST RM0313 section 32.1 Unique device ID register
        # F303/328/358/398, F301/318, F302, F37x
        "F3": 0x1FFFF7AC,
        # ST RM0090 section 39.1 Unique device ID register
        # F405/415, F407/417, F427/437, F429/439
        "F4": 0x1FFF7A10,
        # ST RM0385 section 41.2 Unique device ID register
        "F7": 0x1FF0F420,
        # ST RM0433 section 61.1 Unique device ID register
        "H7": 0x1FF1E800,
        # ST RM0394 47.1 Unique device ID register (96 bits)
        "L4": 0x1FFF7590,
        # ST RM0451 25.2 Unique device ID register (96 bits)
        "L0": 0x1FF80050,
        # ST RM0444 section 38.1 Unique device ID register
        "G0": 0x1FFF7590,
    }

    UID_SWAP = [[1, 0], [3, 2], [7, 6, 5, 4], [11, 10, 9, 8]]

    # Part does not support unique ID feature
    UID_NOT_SUPPORTED = 0
    # stm32loader does not know the address for the unique ID
    UID_ADDRESS_UNKNOWN = -1

    FLASH_SIZE_ADDRESS = {
        # ST RM0360 section 27.1 Memory size data register
        # F030x4/x6/x8/xC, F070x6/xB
        "F0": 0x1FFFF7CC,
        # ST RM0008 section 30.2 Memory size registers
        # F101, F102, F103, F105, F107
        "F1": 0x1FFFF7E0,
        # ST RM0366 section 29.2 Memory size data register
        # ST RM0365 section 34.2 Memory size data register
        # ST RM0316 section 34.2 Memory size data register
        # ST RM0313 section 32.2 Flash memory size data register
        # F303/328/358/398, F301/318, F302, F37x
        "F3": 0x1FFFF7CC,
        # ST RM0090 section 39.2 Flash size
        # F405/415, F407/417, F427/437, F429/439
        "F4": 0x1FFF7A22,
        # ST RM0385 section 41.2 Flash size
        "F7": 0x1FF0F442,
        # ST RM0433 61.2 Flash size
        "H7": 0x1FF1E880,
        # ST RM0394
        "L4": 0x1FFF75E0,
        # ST RM4510 25.1 Memory size register
        "L0": 0x1FF8007C,
        # ST RM0444 section 38.2 Flash memory size data register
        "G0": 0x1FFF75E0,
    }

    DATA_TRANSFER_SIZE = {
        "default": 256,
        # No unique id for these parts
        "F0": 256,  # bytes
        # ST RM0008 section 30.1 Unique device ID register
        # F101, F102, F103, F105, F107
        "F1": 256,  # bytes
        # ST RM0366 section 29.1 Unique device ID register
        # ST RM0365 section 34.1 Unique device ID register
        # ST RM0316 section 34.1 Unique device ID register
        # ST RM0313 section 32.1 Unique device ID register
        # F303/328/358/398, F301/318, F302, F37x
        "F3": 256,  # bytes
        # ST RM0090 section 39.1 Unique device ID register
        # F405/415, F407/417, F427/437, F429/439
        "F4": 256,  # bytes
        # ST RM0385 section 41.2 Unique device ID register
        "F7": 256,  # bytes
        # ST RM0394 47.1 Unique device ID register (96 bits)
        "L4": 256,  # bytes
        # ST RM0451 25.2 Unique device ID register (96 bits)
        "L0": 128,  # bytes
        # ST RM0444 section 38.1 Unique device ID register
        "G0": 256,  # bytes
    }

    FLASH_PAGE_SIZE = {
        "default": 1024,
        # ST RM0360 section 27.1 Memory size data register
        # F030x4/x6/x8/xC, F070x6/xB
        "F0": 1024,  # bytes
        # ST RM0008 section 30.2 Memory size registers
        # F101, F102, F103, F105, F107
        "F1": 1024,  # bytes
        # ST RM0366 section 29.2 Memory size data register
        # ST RM0365 section 34.2 Memory size data register
        # ST RM0316 section 34.2 Memory size data register
        # ST RM0313 section 32.2 Flash memory size data register
        # F303/328/358/398, F301/318, F302, F37x
        "F3": 2048,  # bytes
        # ST RM0090 section 39.2 Flash size
        # F405/415, F407/417, F427/437, F429/439
        "F4": 1024,  # bytes
        # ST RM0385 section 41.2 Flash size
        "F7": 1024,  # bytes
        # ST RM0394
        "L4": 1024,  # bytes
        # ST RM4510 25.1 Memory size register
        "L0": 128,  # bytes
        # ST RM0444 section 38.2 Flash memory size data register
        "G0": 1024,  # bytes
    }

    SYNCHRONIZE_ATTEMPTS = 2

    def __init__(self, connection, device_family=None, verbosity=5, show_progress=None):
        """
        Construct the Stm32Bootloader object.

        The supplied connection can be any object that supports
        read() and write().  Optionally, it may also offer
        enable_reset() and enable_boot0(); it should advertise this by
        setting TOGGLES_RESET and TOGGLES_BOOT0 to True.

        The default implementation is stm32loader.connection.SerialConnection,
        but a straight pyserial serial.Serial object can also be used.

        :param connection: Object supporting read() and write().
          E.g. serial.Serial().
        :param int verbosity: Verbosity level. 0 is quite, 10 is verbose.
        :param ShowProgress show_progress: ShowProgress context manager.
           Set to None to disable progress bar output.
        """
        self.connection = connection
        self.verbosity = verbosity
        self.show_progress = show_progress or ShowProgress(None)
        self.extended_erase = False
        self.data_transfer_size = self.DATA_TRANSFER_SIZE.get(device_family or "default")
        self.flash_page_size = self.FLASH_PAGE_SIZE.get(device_family or "default")
        self.device_family = device_family or "F1"

    def write(self, *data):
        """Write the given data to the MCU."""
        for data_bytes in data:
            if isinstance(data_bytes, int):
                data_bytes = struct.pack("B", data_bytes)
            self.connection.write(data_bytes)

    def write_and_ack(self, message, *data):
        """Write data to the MCU and wait until it replies with ACK."""
        # Note: this is a separate method from write() because a keyword
        # argument after *args was not possible in Python 2
        self.write(*data)
        return self._wait_for_ack(message)

    def debug(self, level, message):
        """Print the given message if its level is low enough."""
        if self.verbosity >= level:
            print(message, file=sys.stderr)

    def reset_from_system_memory(self):
        """Reset the MCU with boot0 enabled to enter the bootloader."""
        self._enable_boot0(True)
        self._reset()

        # Flush the input buffer to avoid reading old data.
        # It's known that the CP2102N at high baudrate fails to flush
        # its buffer when the port is opened.
        if hasattr(self.connection, "flush_input_buffer"):
            self.connection.flush_input_buffer()

        # Try the 0x7F synchronize that selects UART in bootloader mode
        # (see ST application notes AN3155 and AN2606).
        # If we are right after reset, it returns ACK, otherwise first
        # time nothing, then NACK.
        # This is not documented in STM32 docs fully, but ST official
        # tools use the same algorithm.
        # This is likely an artifact/side effect of each command being
        # 2-bytes and having xor of bytes equal to 0xFF.

        for attempt in range(self.SYNCHRONIZE_ATTEMPTS):
            if attempt:
                print("Bootloader activation timeout -- retrying", file=sys.stderr)
            self.write(self.Command.SYNCHRONIZE)
            read_data = bytearray(self.connection.read())

            if read_data and read_data[0] in (self.Reply.ACK, self.Reply.NACK):
                # success
                return

        # not successful
        raise CommandError("Bad reply from bootloader")

    def reset_from_flash(self):
        """Reset the MCU with boot0 disabled."""
        self._enable_boot0(False)
        self._reset()

    def command(self, command, description):
        """
        Send the given command to the MCU.

        Raise CommandError if there's no ACK replied.
        """
        self.debug(10, "*** Command: %s" % description)
        ack_received = self.write_and_ack("Command", command, command ^ 0xFF)
        if not ack_received:
            raise CommandError("%s (%s) failed: no ack" % (description, command))

    def get(self):
        """Return the bootloader version and remember supported commands."""
        self.command(self.Command.GET, "Get")
        length = bytearray(self.connection.read())[0]
        version = bytearray(self.connection.read())[0]
        self.debug(10, "    Bootloader version: " + hex(version))
        data = bytearray(self.connection.read(length))
        if self.Command.EXTENDED_ERASE in data:
            self.extended_erase = True
        self.debug(10, "    Available commands: " + ", ".join(hex(b) for b in data))
        self._wait_for_ack("0x00 end")
        return version

    def get_version(self):
        """
        Return the bootloader version.

        Read protection status readout is not yet implemented.
        """
        self.command(self.Command.GET_VERSION, "Get version")
        data = bytearray(self.connection.read(3))
        version = data[0]
        option_byte1 = data[1]
        option_byte2 = data[2]
        self._wait_for_ack("0x01 end")
        self.debug(10, "    Bootloader version: " + hex(version))
        self.debug(10, "    Option byte 1: " + hex(option_byte1))
        self.debug(10, "    Option byte 2: " + hex(option_byte2))
        return version

    def get_id(self):
        """Send the 'Get ID' command and return the device (model) ID."""
        self.command(self.Command.GET_ID, "Get ID")
        length = bytearray(self.connection.read())[0]
        id_data = bytearray(self.connection.read(length + 1))
        self._wait_for_ack("0x02 end")
        _device_id = reduce(lambda x, y: x * 0x100 + y, id_data)
        return _device_id

    def get_flash_size(self):
        """Return the MCU's flash size in bytes."""
        flash_size_address = self.FLASH_SIZE_ADDRESS[self.device_family]
        flash_size_bytes = self.read_memory(flash_size_address, 2)
        flash_size = flash_size_bytes[0] + (flash_size_bytes[1] << 8)
        return flash_size

    def get_flash_size_and_uid(self):
        """
        Return device_uid and flash_size for L0 and F4 family devices.

        For some reason, F4 (at least, NUCLEO F401RE) can't read the 12 or 2
        bytes for UID and flash size directly.
        Reading a whole chunk of 256 bytes at 0x1FFFA700 does work and
        requires some data extraction.
        """
        flash_size_address = self.FLASH_SIZE_ADDRESS[self.device_family]
        uid_address = self.UID_ADDRESS.get(self.device_family)

        if uid_address is None:
            return None, None

        # Start address is the start of the 256-byte block
        # containing uid_address and flash_size_address.
        data_start_address = uid_address & 0xFFFFFF00
        flash_size_lsb_address = flash_size_address - data_start_address
        uid_lsb_address = uid_address - data_start_address

        self.debug(10, "flash_size_address = 0x%X" % flash_size_address)
        self.debug(10, "uid_address = 0x%X" % uid_address)
        # self.debug(10, 'data_start_address =0x%X' % data_start_address)
        # self.debug(10, 'flashsizelsbaddress =0x%X' % flash_size_lsb_address)
        # self.debug(10, 'uid_lsb_address = 0x%X' % uid_lsb_address)

        data = self.read_memory(data_start_address, self.data_transfer_size)
        device_uid = data[uid_lsb_address : uid_lsb_address + 12]
        flash_size = data[flash_size_lsb_address] + (data[flash_size_lsb_address + 1] << 8)

        return flash_size, device_uid

    def get_uid(self):
        """
        Send the 'Get UID' command and return the device UID.

        Return UID_NOT_SUPPORTED if the device does not have
        a UID.
        Return UIT_ADDRESS_UNKNOWN if the address of the device's
        UID is not known.

        :return byterary: UID bytes of the device, or 0 or -1 when
          not available.
        """
        uid_address = self.UID_ADDRESS.get(self.device_family, self.UID_ADDRESS_UNKNOWN)
        if uid_address is None:
            return self.UID_NOT_SUPPORTED
        if uid_address == self.UID_ADDRESS_UNKNOWN:
            return self.UID_ADDRESS_UNKNOWN

        uid = self.read_memory(uid_address, 12)
        return uid

    @classmethod
    def format_uid(cls, uid):
        """Return a readable string from the given UID."""
        if uid == cls.UID_NOT_SUPPORTED:
            return "UID not supported in this part"
        if uid == cls.UID_ADDRESS_UNKNOWN:
            return "UID address unknown"

        swapped_data = [[uid[b] for b in part] for part in Stm32Bootloader.UID_SWAP]
        uid_string = "-".join("".join(format(b, "02X") for b in part) for part in swapped_data)
        return uid_string

    def read_memory(self, address, length):
        """
        Return the memory contents of flash at the given address.

        Supports maximum 256 bytes.
        """
        if length > self.data_transfer_size:
            raise DataLengthError("Can not read more than 256 bytes at once.")
        self.command(self.Command.READ_MEMORY, "Read memory")
        self.write_and_ack("0x11 address failed", self._encode_address(address))
        nr_of_bytes = (length - 1) & 0xFF
        checksum = nr_of_bytes ^ 0xFF
        self.write_and_ack("0x11 length failed", nr_of_bytes, checksum)
        return bytearray(self.connection.read(length))

    def go(self, address):
        """Send the 'Go' command to start execution of firmware."""
        # pylint: disable=invalid-name
        self.command(self.Command.GO, "Go")
        self.write_and_ack("0x21 go failed", self._encode_address(address))

    def write_memory(self, address, data):
        """
        Write the given data to flash at the given address.

        Supports maximum 256 bytes.
        """
        nr_of_bytes = len(data)
        if nr_of_bytes == 0:
            return
        if nr_of_bytes > self.data_transfer_size:
            raise DataLengthError("Can not write more than 256 bytes at once.")
        self.command(self.Command.WRITE_MEMORY, "Write memory")
        self.write_and_ack("0x31 address failed", self._encode_address(address))

        # pad data length to multiple of 4 bytes
        if nr_of_bytes % 4 != 0:
            padding_bytes = 4 - (nr_of_bytes % 4)
            nr_of_bytes += padding_bytes
            # append value 0xFF: flash memory value after erase
            data = bytearray(data)
            data.extend([0xFF] * padding_bytes)

        self.debug(10, "    %s bytes to write" % [nr_of_bytes])
        checksum = reduce(operator.xor, data, nr_of_bytes - 1)
        self.write_and_ack("0x31 programming failed", nr_of_bytes - 1, data, checksum)
        self.debug(10, "    Write memory done")

    def erase_memory(self, pages=None):
        """
        Erase flash memory at the given pages.

        Set pages to None to erase the full memory ('global erase').

        :param iterable pages: Iterable of integer page addresses, zero-based.
          Set to None to trigger global mass erase.
        """
        if self.extended_erase:
            # Use erase with two-byte addresses.
            self.extended_erase_memory(pages)
            return

        self.command(self.Command.ERASE, "Erase memory")

        if not pages and self.device_family == "L0":
            # Special case: L0 erase should do each page separately.
            flash_size, _uid = self.get_flash_size_and_uid()
            page_count = (flash_size * 1024) // self.flash_page_size
            if page_count > 255:
                raise PageIndexError("Can not erase more than 255 pages for L0 family.")
            pages = range(page_count)
        if pages:
            # page erase, see ST AN3155
            if len(pages) > 255:
                raise PageIndexError(
                    "Can not erase more than 255 pages at once.\n"
                    "Set pages to None to do global erase or supply fewer pages."
                )
            page_count = len(pages) - 1
            page_numbers = bytearray(pages)
            checksum = reduce(operator.xor, page_numbers, page_count)
            self.write(page_count, page_numbers, checksum)
        else:
            # global erase: n=255 (page count)
            self.write(255, 0)

        self._wait_for_ack("0x43 erase failed")
        self.debug(10, "    Erase memory done")

    def extended_erase_memory(self, pages=None):
        """
        Erase flash memory using two-byte addressing at the given pages.

        Set pages to None to erase the full memory.

        Not all devices support the extended erase command.

        :param iterable pages: Iterable of integer page addresses, zero-based.
          Set to None to trigger global mass erase.
        """
        if not pages and self.device_family in ('L0', ):
            flash_size, _uid = self.get_flash_size_and_uid()
            pages = list(range(0, (flash_size*1024) // self.flash_page_size))

        self.command(self.Command.EXTENDED_ERASE, "Extended erase memory")
        if pages:
            # page erase, see ST AN3155
            if len(pages) > 65535:
                raise PageIndexError(
                    "Can not erase more than 65535 pages at once.\n"
                    "Set pages to None to do global erase or supply fewer pages."
                )
            page_count = (len(pages) & 0xFFFF) - 1
            page_count_bytes = bytearray(struct.pack(">H", page_count))
            page_bytes = bytearray(len(pages) * 2)
            for i, page in enumerate(pages):
                struct.pack_into(">H", page_bytes, i * 2, page)
            checksum = reduce(operator.xor, page_count_bytes)
            checksum = reduce(operator.xor, page_bytes, checksum)
            self.write(page_count_bytes, page_bytes, checksum)
        else:
            # global mass erase: n=0xffff (page count) + checksum
            # TO DO: support 0xfffe bank 1 erase / 0xfffe bank 2 erase
            self.write(b"\xff\xff\x00")

        previous_timeout_value = self.connection.timeout
        self.connection.timeout = 30
        print("Extended erase (0x44), this can take ten seconds or more")
        try:
            self._wait_for_ack("0x44 erasing failed")
        finally:
            self.connection.timeout = previous_timeout_value
        self.debug(10, "    Extended Erase memory done")

    def write_protect(self, pages):
        """Enable write protection on the given flash pages."""
        self.command(self.Command.WRITE_PROTECT, "Write protect")
        nr_of_pages = (len(pages) - 1) & 0xFF
        page_numbers = bytearray(pages)
        checksum = reduce(operator.xor, page_numbers, nr_of_pages)
        self.write_and_ack("0x63 write protect failed", nr_of_pages, page_numbers, checksum)
        self.debug(10, "    Write protect done")

    def write_unprotect(self):
        """Disable write protection of the flash memory."""
        self.command(self.Command.WRITE_UNPROTECT, "Write unprotect")
        self._wait_for_ack("0x73 write unprotect failed")
        self.debug(10, "    Write Unprotect done")

    def readout_protect(self):
        """Enable readout protection of the flash memory."""
        self.command(self.Command.READOUT_PROTECT, "Readout protect")
        self._wait_for_ack("0x82 readout protect failed")
        self.debug(10, "    Read protect done")

    def readout_unprotect(self):
        """
        Disable readout protection of the flash memory.

        Beware, this will erase the flash content.
        """
        self.command(self.Command.READOUT_UNPROTECT, "Readout unprotect")
        self._wait_for_ack("0x92 readout unprotect failed")
        self.debug(20, "    Mass erase -- this may take a while")
        time.sleep(20)
        self.debug(20, "    Unprotect / mass erase done")
        self.debug(20, "    Reset after automatic chip reset due to readout unprotect")
        self.reset_from_system_memory()

    def read_memory_data(self, address, length):
        """
        Return flash content from the given address and byte count.

        Length may be more than 256 bytes.
        """
        data = bytearray()
        chunk_count = int(math.ceil(length / float(self.data_transfer_size)))
        self.debug(5, "Read %d chunks at address 0x%X..." % (chunk_count, address))
        with self.show_progress("Reading", maximum=chunk_count) as progress_bar:
            while length:
                read_length = min(length, self.data_transfer_size)
                self.debug(
                    10,
                    "Read %(len)d bytes at 0x%(address)X"
                    % {"address": address, "len": read_length},
                )
                data = data + self.read_memory(address, read_length)
                progress_bar.next()
                length = length - read_length
                address = address + read_length
        return data

    def write_memory_data(self, address, data):
        """
        Write the given data to flash.

        Data length may be more than 256 bytes.
        """
        length = len(data)
        chunk_count = int(math.ceil(length / float(self.data_transfer_size)))
        offset = 0
        self.debug(5, "Write %d chunks at address 0x%X..." % (chunk_count, address))

        with self.show_progress("Writing", maximum=chunk_count) as progress_bar:
            while length:
                write_length = min(length, self.data_transfer_size)
                self.debug(
                    10,
                    "Write %(len)d bytes at 0x%(address)X"
                    % {"address": address, "len": write_length},
                )
                self.write_memory(address, data[offset : offset + write_length])
                progress_bar.next()
                length -= write_length
                offset += write_length
                address += write_length

    @staticmethod
    def verify_data(read_data, reference_data):
        """
        Raise an error if the given data does not match its reference.

        Error type is DataMismatchError.

        :param read_data: Data to compare.
        :param reference_data: Data to compare, as reference.
        :return None:
        """
        if read_data == reference_data:
            return

        if len(read_data) != len(reference_data):
            raise DataMismatchError(
                "Data length does not match: %d bytes vs %d bytes."
                % (len(read_data), len(reference_data))
            )

        # data differs; find out where and raise VerifyError
        for address, data_pair in enumerate(zip(reference_data, read_data)):
            reference_byte, read_byte = data_pair
            if reference_byte != read_byte:
                raise DataMismatchError(
                    "Verification data does not match read data. "
                    "First mismatch at address: 0x%X read 0x%X vs 0x%X expected."
                    % (address, bytearray([read_byte])[0], bytearray([reference_byte])[0])
                )

    def _reset(self):
        """Enable or disable the reset IO line (if possible)."""
        if not hasattr(self.connection, "enable_reset"):
            return
        self.connection.enable_reset(True)
        time.sleep(0.1)
        self.connection.enable_reset(False)
        time.sleep(0.5)

    def _enable_boot0(self, enable=True):
        """Enable or disable the boot0 IO line (if possible)."""
        if not hasattr(self.connection, "enable_boot0"):
            return

        self.connection.enable_boot0(enable)

    def _wait_for_ack(self, info=""):
        """Read a byte and raise CommandError if it's not ACK."""
        read_data = bytearray(self.connection.read())
        if not read_data:
            raise CommandError("Can't read port or timeout")
        reply = read_data[0]
        if reply == self.Reply.NACK:
            raise CommandError("NACK " + info)
        if reply != self.Reply.ACK:
            raise CommandError("Unknown response. " + info + ": " + hex(reply))

        return 1

    @staticmethod
    def _encode_address(address):
        """Return the given address as big-endian bytes with a checksum."""
        # address in four bytes, big-endian
        address_bytes = bytearray(struct.pack(">I", address))
        # checksum as single byte
        checksum_byte = struct.pack("B", reduce(operator.xor, address_bytes))
        return address_bytes + checksum_byte
