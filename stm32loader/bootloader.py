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


from __future__ import print_function

import sys
import time
from functools import reduce

CHIP_IDS = {
    # see ST AN2606 Table 116 Bootloader device-dependent parameters
    # 16 to 32 KiB
    0x412: "STM32F10x Low-density",
    # 64 to 128 KiB
    0x410: "STM32F10x Medium-density",
    0x420: "STM32F10x Medium-density value line",
    # 256 to 512 KiB (5128 Kbyte is probably a typo?)
    0x414: "STM32F10x High-density",
    0x428: "STM32F10x High-density value line",
    # 768 to 1024 KiB
    0x430: "STM3210xx XL-density",
    # flash size to be looked up
    0x416: "STM32L1xxx6(8/B) Medium-density ultralow power line",
    0x411: "STM32F2xxx",
    0x413: "STM32F40xxx/41xxx",
    0x419: "STM3242xxx/43xxx",
    0x449: "STM32F74xxx/75xxx",
    0x451: "STM32F76xxx/77xxx",
    # see ST AN4872
    # requires parity None
    0x11103: "BlueNRG",
    # other
    # Cortex-M0 MCU with hardware TCP/IP and MAC
    # (SweetPeas custom bootloader)
    0x801: "Wiznet W7500",
}


class CommandException(IOError):
    """Error: a command in the STM32 native bootloader failed."""


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
        # ST RM0008 section 30.1 Unique device ID register
        # F101, F102, F103, F105, F107
        "F1": 0x1FFFF7E8,
        # ST RM0090 section 39.1 Unique device ID register
        # F405/415, F407/417, F427/437, F429/439
        "F4": 0x1FFFF7A10,
        # ST RM0385 section 41.2 Unique device ID register
        "F7": 0x1FF0F420,
    }

    UID_SWAP = [[1, 0], [3, 2], [7, 6, 5, 4], [11, 10, 9, 8]]

    FLASH_SIZE_ADDRESS = {
        # ST RM0008 section 30.2 Memory size registers
        # F101, F102, F103, F105, F107
        "F1": 0x1FFFF7E0,
        # ST RM0090 section 39.2 Flash size
        # F405/415, F407/417, F427/437, F429/439
        "F4": 0x1FFF7A22,
        # ST RM0385 section 41.2 Flash size
        "F7": 0x1FF0F442,
    }

    extended_erase = False

    def __init__(self, connection, verbosity=5):
        """
        Construct the Stm32Bootloader object.

        The supplied connection can be any object that supports
        read() and write().  Optionally, it may also offer
        enable_reset() and enable_boot0; it should advertize this by
        setting TOGGLES_RESET and TOGGLES_BOOT0 to True.

        The default implementation is stm32loader.connection.SerialConnection,
        but a straight pyserial serial.Serial object can also be used.


        :param connection: Object supporting read() and write().
          E.g. serial.Serial().
        :param int verbosity: Verbosity level. 0 is quite, 10 is verbose.
        """
        self.connection = connection
        self._toggle_reset = getattr(connection, "can_toggle_reset", False)
        self._toggle_boot0 = getattr(connection, "can_toggle_boot0", False)
        self.verbosity = verbosity

    def debug(self, level, message):
        if self.verbosity >= level:
            print(message, file=sys.stderr)

    def reset_from_system_memory(self):
        self._enable_boot0(True)
        self._reset()
        self.connection.write(bytearray([self.Command.SYNCHRONIZE]))
        return self._wait_for_ack("Syncro")

    def reset_from_flash(self):
        self._enable_boot0(False)
        self._reset()

    def command(self, command):
        command_byte = bytearray([command])
        control_byte = bytearray([command ^ 0xFF])

        self.connection.write(command_byte)
        self.connection.write(control_byte)

        return self._wait_for_ack(hex(command))

    def get(self):
        if not self.command(self.Command.GET):
            raise CommandException("Get (0x00) failed")
        self.debug(10, "*** Get command")
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
        if not self.command(self.Command.GET_VERSION):
            raise CommandException("GetVersion (0x01) failed")

        self.debug(10, "*** GetVersion command")
        version = bytearray(self.connection.read())[0]
        self.connection.read(2)
        self._wait_for_ack("0x01 end")
        self.debug(10, "    Bootloader version: " + hex(version))
        return version

    def get_id(self):
        if not self.command(self.Command.GET_ID):
            raise CommandException("GetID (0x02) failed")

        self.debug(10, "*** GetID command")
        length = bytearray(self.connection.read())[0]
        id_data = bytearray(self.connection.read(length + 1))
        self._wait_for_ack("0x02 end")
        _device_id = reduce(lambda x, y: x * 0x100 + y, id_data)
        return _device_id

    def get_flash_size(self, device_family):
        flash_size_address = self.FLASH_SIZE_ADDRESS[device_family]
        flash_size_bytes = self.read_memory(flash_size_address, 2)
        flash_size = flash_size_bytes[0] + flash_size_bytes[1] * 256
        return flash_size

    def get_uid(self, device_id):
        uid_address = self.UID_ADDRESS[device_id]
        uid = self.read_memory(uid_address, 12)
        return uid

    @staticmethod
    def format_uid(uid):
        swapped_data = [[uid[b] for b in part] for part in Stm32Bootloader.UID_SWAP]
        uid_string = "-".join("".join(format(b, "02X") for b in part) for part in swapped_data)
        return uid_string

    def read_memory(self, address, length):
        assert length <= 256
        if not self.command(self.Command.READ_MEMORY):
            raise CommandException("ReadMemory (0x11) failed")

        self.debug(10, "*** ReadMemory command")
        self.connection.write(self._encode_address(address))
        self._wait_for_ack("0x11 address failed")
        nr_of_bytes = (length - 1) & 0xFF
        checksum = nr_of_bytes ^ 0xFF
        self.connection.write(bytearray([nr_of_bytes, checksum]))
        self._wait_for_ack("0x11 length failed")
        return bytearray(self.connection.read(length))

    def go(self, address):
        # pylint: disable=invalid-name
        if not self.command(self.Command.GO):
            raise CommandException("Go (0x21) failed")

        self.debug(10, "*** Go command")
        self.connection.write(self._encode_address(address))
        self._wait_for_ack("0x21 go failed")

    def write_memory(self, address, data):
        nr_of_bytes = len(data)
        if nr_of_bytes == 0:
            return
        assert nr_of_bytes <= 256

        if not self.command(self.Command.WRITE_MEMORY):
            raise CommandException("Write memory (0x31) failed")

        self.debug(10, "*** Write memory command")
        self.connection.write(self._encode_address(address))
        self._wait_for_ack("0x31 address failed")

        # pad data length to multiple of 4 bytes
        if nr_of_bytes % 4 != 0:
            padding_bytes = 4 - (nr_of_bytes % 4)
            nr_of_bytes += padding_bytes
            # append value 0xFF: flash memory value after erase
            data = bytearray(data)
            data.extend([0xFF] * padding_bytes)

        self.debug(10, "    %s bytes to write" % [nr_of_bytes])
        self.connection.write(bytearray([nr_of_bytes - 1]))
        checksum = nr_of_bytes - 1
        for data_byte in data:
            checksum = checksum ^ data_byte
        self.connection.write(bytearray(data))
        self.connection.write(bytearray([checksum]))
        self._wait_for_ack("0x31 programming failed")
        self.debug(10, "    Write memory done")

    def erase_memory(self, sectors=None):
        if self.extended_erase:
            self.extended_erase_memory()
            return

        if not self.command(self.Command.ERASE):
            raise CommandException("Erase memory (0x43) failed")

        self.debug(10, "*** Erase memory command")

        if sectors:
            self._page_erase(sectors)
        else:
            self._global_erase()
        self._wait_for_ack("0x43 erase failed")
        self.debug(10, "    Erase memory done")

    def extended_erase_memory(self):
        if not self.command(self.Command.EXTENDED_ERASE):
            raise CommandException("Extended Erase memory (0x44) failed")

        self.debug(10, "*** Extended Erase memory command")
        # Global mass erase and checksum byte
        self.connection.write(b"\xFF")
        self.connection.write(b"\xFF")
        self.connection.write(b"\x00")
        previous_timeout_value = self.connection.timeout
        self.connection.timeout = 30
        print("Extended erase (0x44), this can take ten seconds or more")
        self._wait_for_ack("0x44 erasing failed")
        self.connection.timeout = previous_timeout_value
        self.debug(10, "    Extended Erase memory done")

    def write_protect(self, pages):
        if not self.command(self.Command.WRITE_PROTECT):
            raise CommandException("Write Protect memory (0x63) failed")

        self.debug(10, "*** Write protect command")
        nr_of_pages = (len(pages) - 1) & 0xFF
        self.connection.write(bytearray([nr_of_pages]))
        checksum = 0xFF
        for page_index in pages:
            checksum = checksum ^ page_index
            self.connection.write(bytearray([page_index]))
        self.connection.write(bytearray([checksum]))
        self._wait_for_ack("0x63 write protect failed")
        self.debug(10, "    Write protect done")

    def write_unprotect(self):
        if not self.command(self.Command.WRITE_UNPROTECT):
            raise CommandException("Write Unprotect (0x73) failed")

        self.debug(10, "*** Write Unprotect command")
        self._wait_for_ack("0x73 write unprotect failed")
        self.debug(10, "    Write Unprotect done")

    def readout_protect(self):
        if not self.command(self.Command.READOUT_PROTECT):
            raise CommandException("Readout protect (0x82) failed")

        self.debug(10, "*** Readout protect command")
        self._wait_for_ack("0x82 readout protect failed")
        self.debug(10, "    Read protect done")

    def readout_unprotect(self):
        if not self.command(self.Command.READOUT_UNPROTECT):
            raise CommandException("Readout unprotect (0x92) failed")

        self.debug(10, "*** Readout Unprotect command")
        self._wait_for_ack("0x92 readout unprotect failed")
        self.debug(20, "    Mass erase -- this may take a while")
        time.sleep(20)
        self.debug(20, "    Unprotect / mass erase done")
        self.debug(20, "    Reset after automatic chip reset due to readout unprotect")
        self.reset_from_system_memory()

    def read_memory_data(self, address, length):
        data = bytearray()
        while length > 256:
            self.debug(
                5, "Read %(len)d bytes at 0x%(address)X" % {"address": address, "len": 256}
            )
            data = data + self.read_memory(address, 256)
            address = address + 256
            length = length - 256
        if length:
            self.debug(
                5, "Read %(len)d bytes at 0x%(address)X" % {"address": address, "len": length}
            )
            data = data + self.read_memory(address, length)
        return data

    def write_memory_data(self, address, data):
        length = len(data)
        offset = 0
        while length > 256:
            self.debug(
                5, "Write %(len)d bytes at 0x%(address)X" % {"address": address, "len": 256}
            )
            self.write_memory(address, data[offset : offset + 256])
            offset += 256
            address += 256
            length -= 256
        if length:
            self.debug(
                5, "Write %(len)d bytes at 0x%(address)X" % {"address": address, "len": length}
            )
            self.write_memory(address, data[offset : offset + length])

    def _global_erase(self):
        # global erase: n=255, see ST AN3155
        self.connection.write(b"\xff")
        self.connection.write(b"\x00")

    def _page_erase(self, pages):
        # page erase, see ST AN3155
        nr_of_pages = (len(pages) - 1) & 0xFF
        self.connection.write(bytearray([nr_of_pages]))
        checksum = nr_of_pages
        for page_number in pages:
            self.connection.write(bytearray([page_number]))
            checksum = checksum ^ page_number
        self.connection.write(bytearray([checksum]))

    def _reset(self):
        if not self._toggle_reset:
            return
        self.connection.enable_reset(True)
        time.sleep(0.1)
        self.connection.enable_reset(False)
        time.sleep(0.5)

    def _enable_boot0(self, enable=True):
        if not self._toggle_boot0:
            return

        self.connection.enable_boot0(enable)

    def _wait_for_ack(self, info=""):
        try:
            ack = bytearray(self.connection.read())[0]
        except TypeError:
            raise CommandException("Can't read port or timeout")

        if ack == self.Reply.NACK:
            raise CommandException("NACK " + info)

        if ack != self.Reply.ACK:
            raise CommandException("Unknown response. " + info + ": " + hex(ack))

        return 1

    @staticmethod
    def _encode_address(address):
        byte3 = (address >> 0) & 0xFF
        byte2 = (address >> 8) & 0xFF
        byte1 = (address >> 16) & 0xFF
        byte0 = (address >> 24) & 0xFF
        checksum = byte0 ^ byte1 ^ byte2 ^ byte3
        return bytearray([byte0, byte1, byte2, byte3, checksum])
