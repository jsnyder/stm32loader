#!/usr/bin/env python

# -*- coding: utf-8 -*-
# vim: sw=4:ts=4:si:et:enc=utf-8

# Author: Ivan A-R <ivan@tuxotronic.org>
# GitHub repository: https://github.com/jsnyder/stm32loader
#
# This file is part of stm32loader.
#
# stm32loader is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation; either version 3, or (at your option) any later
# version.
#
# stm32loader is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.
#
# You should have received a copy of the GNU General Public License
# along with stm32loader; see the file COPYING3.  If not see
# <http://www.gnu.org/licenses/>.


from __future__ import print_function

from functools import reduce
import sys
import getopt
import serial
import time


VERSION = (0, 3, 0)
__version__ = '.'.join(map(str, VERSION))

VERBOSITY = 20

CHIP_IDS = {
    # see ST AN2606
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

    # see ST AN4872
    # requires parity None
    0x11103: "BlueNRG",

    # other

    # Cortex-M0 MCU with hardware TCP/IP and MAC
    # (SweetPeas custom bootloader)
    0x801: "Wiznet W7500",
}


def debug(level, message):
    if VERBOSITY >= level:
        print(message, file=sys.stderr)


class CommandException(Exception):
    pass


class Stm32Bootloader:

    class Command:
        # See ST AN3155
        GET = 0x00
        GET_VERSION = 0x01
        GET_ID = 0x02
        READ_MEMORY = 0x11
        GO = 0x21
        WRITE_MEMORY = 0x31
        ERASE = 0x43
        EXTENDED_ERASE = 0x44
        WRITE_PROTECT = 0x63
        WRITE_UNPROTECT = 0x73
        READOUT_PROTECT = 0x82
        READOUT_UNPROTECT = 0x92
        # not really listed under commands, but still...
        # 'wake the bootloader' == 'activate USART' == 'synchronize'
        SYNCHRONIZE = 0x7F

    class Reply:
        # See ST AN3155
        ACK = 0x79
        NACK = 0x1F

    PARITY = dict(
        even=serial.PARITY_EVEN,
        none=serial.PARITY_NONE,
    )

    UID_ADDRESS = {
        # ST RM0008 section 30.1 Unique device ID register
        # F101, F102, F103, F105, F107
        'F1': 0x1FFFF7E8,
        # ST RM0090 section 39.1 Unique device ID register
        # F405/415, F407/417, F427/437, F429/439
        'F4': 0x1FFFF7A10,
    }

    FLASH_SIZE_ADDRESS = {
        # ST RM0008 section 30.2 Memory size registers
        # F101, F102, F103, F105, F107
        'F1': 0x1FFFF7E0,
        # ST RM0090 section 39.2 Unique device ID register
        # F405/415, F407/417, F427/437, F429/439
        'F4': 0x1FFF7A22,
    }

    extended_erase = False

    def __init__(self, swap_rts_dtr=False, reset_active_high=False, boot0_active_high=False):
        self.serial = None
        self._swap_RTS_DTR = swap_rts_dtr
        self._reset_active_high = reset_active_high
        self._boot0_active_high = boot0_active_high

    def open(self, serial_port, baud_rate=115200, parity=serial.PARITY_EVEN):
        try:
            self.serial = serial.Serial(
                port=serial_port,
                baudrate=baud_rate,
                # number of write_data bits
                bytesize=8,
                parity=parity,
                stopbits=1,
                # don't enable software flow control
                xonxoff=0,
                # don't enable RTS/CTS flow control
                rtscts=0,
                # set a timeout value, None for waiting forever
                timeout=5,
            )
        except serial.serialutil.SerialException as e:
            sys.stderr.write(str(e) + "\n")
            sys.stderr.write(
                "Is the device connected and powered correctly?\n"
                "Please use the -p option to select the correct serial port. Examples:\n"
                "  -p COM3\n"
                "  -p /dev/ttyS0\n"
                "  -p /dev/ttyUSB0\n"
                "  -p /dev/tty.usbserial-ftCYPMYJ\n"
            )
            exit(1)

    def reset_from_system_memory(self):
        self._enable_boot0(True)
        self._reset()
        self.serial.write(bytearray([self.Command.SYNCHRONIZE]))
        return self._wait_for_ack("Syncro")

    def reset_from_flash(self):
        self._enable_boot0(False)
        self._reset()

    def command(self, command):
        command_byte = bytearray([command])
        control_byte = bytearray([command ^ 0xFF])

        self.serial.write(command_byte)
        self.serial.write(control_byte)

        return self._wait_for_ack(hex(command))

    def get(self):
        if not self.command(self.Command.GET):
            raise CommandException("Get (0x00) failed")
        debug(10, "*** Get command")
        length = bytearray(self.serial.read())[0]
        version = bytearray(self.serial.read())[0]
        debug(10, "    Bootloader version: " + hex(version))
        data = bytearray(self.serial.read(length))
        if self.Command.EXTENDED_ERASE in data:
            self.extended_erase = True
        debug(10, "    Available commands: " + ", ".join(hex(b) for b in data))
        self._wait_for_ack("0x00 end")
        return version

    def get_version(self):
        if not self.command(self.Command.GET_VERSION):
            raise CommandException("GetVersion (0x01) failed")

        debug(10, "*** GetVersion command")
        version = bytearray(self.serial.read())[0]
        self.serial.read(2)
        self._wait_for_ack("0x01 end")
        debug(10, "    Bootloader version: " + hex(version))
        return version

    def get_id(self):
        if not self.command(self.Command.GET_ID):
            raise CommandException("GetID (0x02) failed")

        debug(10, "*** GetID command")
        length = bytearray(self.serial.read())[0]
        id_data = bytearray(self.serial.read(length + 1))
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
        UID_SWAP = [[1, 0], [3, 2], [7, 6, 5, 4], [11, 10, 9, 8]]
        swapped_data = [[uid[b] for b in part] for part in UID_SWAP]
        uid_string = '-'.join(''.join(format(b, '02X') for b in part) for part in swapped_data)
        return uid_string

    def read_memory(self, address, length):
        assert(length <= 256)
        if not self.command(self.Command.READ_MEMORY):
            raise CommandException("ReadMemory (0x11) failed")

        debug(10, "*** ReadMemory command")
        self.serial.write(self._encode_address(address))
        self._wait_for_ack("0x11 address failed")
        nr_of_bytes = (length - 1) & 0xFF
        checksum = nr_of_bytes ^ 0xFF
        self.serial.write(bytearray([nr_of_bytes, checksum]))
        self._wait_for_ack("0x11 length failed")
        return bytearray(self.serial.read(length))

    def go(self, address):
        if not self.command(self.Command.GO):
            raise CommandException("Go (0x21) failed")

        debug(10, "*** Go command")
        self.serial.write(self._encode_address(address))
        self._wait_for_ack("0x21 go failed")

    def write_memory(self, address, data):
        assert(len(data) <= 256)
        if not self.command(self.Command.WRITE_MEMORY):
            raise CommandException("Write memory (0x31) failed")

        debug(10, "*** Write memory command")
        self.serial.write(self._encode_address(address))
        self._wait_for_ack("0x31 address failed")
        nr_of_bytes = (len(data) - 1) & 0xFF
        debug(10, "    %s bytes to write" % [nr_of_bytes + 1])
        self.serial.write(bytearray([nr_of_bytes]))
        checksum = 0xFF
        for c in data:
            checksum = checksum ^ c
            self.serial.write(bytearray([c]))
        self.serial.write(bytearray([checksum]))
        self._wait_for_ack("0x31 programming failed")
        debug(10, "    Write memory done")

    def erase_memory(self, sectors=None):
        if self.extended_erase:
            return bootloader.extended_erase_memory()

        if not self.command(self.Command.ERASE):
            raise CommandException("Erase memory (0x43) failed")

        debug(10, "*** Erase memory command")

        if sectors:
            self._page_erase(sectors)
        else:
            self._global_erase()
        self._wait_for_ack("0x43 erase failed")
        debug(10, "    Erase memory done")

    def extended_erase_memory(self):
        if not self.command(self.Command.EXTENDED_ERASE):
            raise CommandException("Extended Erase memory (0x44) failed")

        debug(10, "*** Extended Erase memory command")
        # Global mass erase and checksum byte
        self.serial.write(b'\xFF')
        self.serial.write(b'\xFF')
        self.serial.write(b'\x00')
        previous_timeout_value = self.serial.timeout
        self.serial.timeout = 30
        print("Extended erase (0x44), this can take ten seconds or more")
        self._wait_for_ack("0x44 erasing failed")
        self.serial.timeout = previous_timeout_value
        debug(10, "    Extended Erase memory done")

    def write_protect(self, pages):
        if not self.command(self.Command.WRITE_PROTECT):
            raise CommandException("Write Protect memory (0x63) failed")

        debug(10, "*** Write protect command")
        nr_of_pages = (len(pages) - 1) & 0xFF
        self.serial.write(bytearray([nr_of_pages]))
        checksum = 0xFF
        for c in pages:
            checksum = checksum ^ c
            self.serial.write(bytearray([c]))
        self.serial.write(bytearray([checksum]))
        self._wait_for_ack("0x63 write protect failed")
        debug(10, "    Write protect done")

    def write_unprotect(self):
        if not self.command(self.Command.WRITE_UNPROTECT):
            raise CommandException("Write Unprotect (0x73) failed")

        debug(10, "*** Write Unprotect command")
        self._wait_for_ack("0x73 write unprotect failed")
        self._wait_for_ack("0x73 write unprotect 2 failed")
        debug(10, "    Write Unprotect done")

    def readout_protect(self):
        if not self.command(self.Command.READOUT_PROTECT):
            raise CommandException("Readout protect (0x82) failed")

        debug(10, "*** Readout protect command")
        self._wait_for_ack("0x82 readout protect failed")
        self._wait_for_ack("0x82 readout protect 2 failed")
        debug(10, "    Read protect done")

    def readout_unprotect(self):
        if not self.command(self.Command.READOUT_UNPROTECT):
            raise CommandException("Readout unprotect (0x92) failed")

        debug(10, "*** Readout Unprotect interface")
        self._wait_for_ack("0x92 readout unprotect failed")
        self._wait_for_ack("0x92 readout unprotect 2 failed")
        debug(10, "    Read Unprotect done")

    def read_memory_data(self, address, length):
        data = bytearray()
        while length > 256:
            debug(5, "Read %(len)d bytes at 0x%(address)X" % {'address': address, 'len': 256})
            data = data + self.read_memory(address, 256)
            address = address + 256
            length = length - 256
        else:
            debug(5, "Read %(len)d bytes at 0x%(address)X" % {'address': address, 'len': 256})
        data = data + self.read_memory(address, length)
        return data

    def write_memory_data(self, address, data):
        length = len(data)
        offset = 0
        while length > 256:
            debug(5, "Write %(len)d bytes at 0x%(address)X" % {'address': address, 'len': 256})
            self.write_memory(address, data[offset:offset + 256])
            offset += 256
            address += 256
            length -= 256
        else:
            debug(5, "Write %(len)d bytes at 0x%(address)X" % {'address': address, 'len': 256})
        self.write_memory(address, data[offset:offset + length] + (b'\xff' * (256 - length)))

    def _global_erase(self):
        # global erase: n=255, see ST AN3155
        self.serial.write(b'\xff')
        self.serial.write(b'\x00')

    def _page_erase(self, pages):
        # page erase, see ST AN3155
        nr_of_pages = (len(pages) - 1) & 0xFF
        self.serial.write(bytearray([nr_of_pages]))
        checksum = nr_of_pages
        for page_number in pages:
            self.serial.write(bytearray([page_number]))
            checksum = checksum ^ page_number
        self.serial.write(bytearray([checksum]))

    def _reset(self):
        self._enable_reset(True)
        time.sleep(0.1)
        self._enable_reset(False)
        time.sleep(0.5)

    def _enable_reset(self, enable=True):
        # reset on the MCU is active low (0 Volt puts the MCU in reset)
        # but RS-232 DTR is active low by itself so it inverts this
        # (writing logical 1 outputs a low voltage)
        level = 1 if enable else 0

        # setting -R (reset active high) ensures that the MCU
        # gets 3.3 Volt to enable reset
        if self._reset_active_high:
            level = 1 - level

        if self._swap_RTS_DTR:
            self.serial.setRTS(level)
        else:
            self.serial.setDTR(level)

    def _enable_boot0(self, enable=True):
        # active low unless otherwise specified
        level = 0 if enable else 1

        if self._boot0_active_high:
            # enabled by argument -B (boot0 active high)
            level = 1 - level

        if self._swap_RTS_DTR:
            self.serial.setDTR(level)
        else:
            self.serial.setRTS(level)

    def _wait_for_ack(self, info=""):
        try:
            ack = bytearray(self.serial.read())[0]
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


def usage():
    help_text = """Usage: %s [-hqVewvrsRB] [-l length] [-p port] [-b baud] [-P parity] [-a address] [-g address] [-f family] [file.bin]
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

    ./stm32loader.py -e -w -v example/main.bin
    """
    help_text = help_text % sys.argv[0]
    print(help_text)


if __name__ == "__main__":
    
    configuration = {
        'port': '/dev/tty.usbserial-ftCYPMYJ',
        'baud': 115200,
        'parity': serial.PARITY_EVEN,
        'address': 0x08000000,
        'erase': False,
        'write': False,
        'verify': False,
        'read': False,
        'go_address': -1,
        'swap_rts_dtr': False,
        'reset_active_high': False,
        'boot0_active_high': False,
        'family': None,
    }

    try:
        # parse command-line arguments using getopt
        opts, args = getopt.getopt(sys.argv[1:], "hqVewvrsRBP:f:p:b:a:l:g:")
    except getopt.GetoptError as err:
        # print help information and exit:
        # this print something like "option -a not recognized"
        print(str(err))
        usage()
        sys.exit(2)

    VERBOSITY = 5

    for option, value in opts:
        if option == '-V':
            VERBOSITY = 10
        elif option == '-q':
            VERBOSITY = 0
        elif option == '-h':
            usage()
            sys.exit(0)
        elif option == '-e':
            configuration['erase'] = True
        elif option == '-w':
            configuration['write'] = True
        elif option == '-v':
            configuration['verify'] = True
        elif option == '-r':
            configuration['read'] = True
        elif option == '-p':
            configuration['port'] = value
        elif option == '-s':
            configuration['swap_rts_dtr'] = True
        elif option == '-R':
            configuration['reset_active_high'] = True
        elif option == '-B':
            configuration['boot0_active_high'] = True
        elif option == '-b':
            configuration['baud'] = eval(value)
        elif option == '-P':
            assert value.lower() in Stm32Bootloader.PARITY, "Parity value not recognized: '{0}'.".format(value)
            configuration['parity'] = Stm32Bootloader.PARITY[value.lower()]
        elif option == '-a':
            configuration['address'] = eval(value)
        elif option == '-g':
            configuration['go_address'] = eval(value)
        elif option == '-l':
            configuration['length'] = eval(value)
        elif option == '-f':
            configuration['family'] = value
        else:
            assert False, "unhandled option %s" % option

    bootloader = Stm32Bootloader(
        swap_rts_dtr=configuration['swap_rts_dtr'],
        reset_active_high=configuration['reset_active_high'],
        boot0_active_high=configuration['boot0_active_high'],
    )
    bootloader.open(
        configuration['port'],
        configuration['baud'],
        configuration['parity'],
    )
    debug(10, "Open port %(port)s, baud %(baud)d" % {'port': configuration['port'], 'baud': configuration['baud']})
    try:
        try:
            bootloader.reset_from_system_memory()
        except Exception:
            print("Can't init. Ensure that BOOT0 is enabled and reset device")

        boot_version = bootloader.get()
        high = (boot_version & 0xF0) >> 4
        low = boot_version & 0x0F
        debug(0, "Bootloader version: V%d.%d" % (high, low))
        device_id = bootloader.get_id()
        debug(0, "Chip ID: 0x%x (%s)" % (device_id, CHIP_IDS.get(device_id, "Unknown")))

        family = configuration['family']
        if not family:
            debug(0, "Supply -f [family] to see flash size and device UID, e.g: -f F1")
        else:
            device_uid = bootloader.get_uid(family)
            device_uid_string = bootloader.format_uid(device_uid)
            debug(0, "Device UID: %s" % device_uid_string)

            flash_size = bootloader.get_flash_size(family)
            debug(0, "Flash size: %d KiB" % flash_size)

        binary_data = None
        # if there's a non-named argument left, that's a file name
        data_file = args[0] if args else None

        if configuration['write'] or configuration['verify']:
            with open(data_file, 'rb') as read_file:
                binary_data = bytearray(read_file.read())

        if configuration['erase']:
            bootloader.erase_memory()

        if configuration['write']:
            bootloader.write_memory_data(configuration['address'], binary_data)

        if configuration['verify']:
            read_data = bootloader.read_memory_data(configuration['address'], len(binary_data))
            if binary_data == read_data:
                print("Verification OK")
            else:
                print("Verification FAILED")
                print(str(len(binary_data)) + ' vs ' + str(len(read_data)))
                for i in range(0, len(binary_data)):
                    if binary_data[i] != read_data[i]:
                        print(hex(i) + ': ' + hex(binary_data[i]) + ' vs ' + hex(read_data[i]))

        if not configuration['write'] and configuration['read']:
            read_data = bootloader.read_memory_data(configuration['address'], configuration['length'])
            with open(data_file, 'wb') as out_file:
                out_file.write(read_data)

        if configuration['go_address'] != -1:
            bootloader.go(configuration['go_address'])

    finally:
        bootloader.reset_from_flash()
