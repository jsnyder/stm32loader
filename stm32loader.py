#!/usr/bin/env python

# -*- coding: utf-8 -*-
# vim: sw=4:ts=4:si:et:enc=utf-8

# Author: Ivan A-R <ivan@tuxotronic.org>
# Project page: http://tuxotronic.org/wiki/projects/stm32loader
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

from functools import reduce
import sys
import getopt
import serial
import time

# Verbose level
QUIET = 20

# these come from AN2606
chip_ids = {
    0x412: "STM32 Low-density",
    0x410: "STM32 Medium-density",
    0x414: "STM32 High-density",
    0x420: "STM32 Medium-density value line",
    0x428: "STM32 High-density value line",
    0x430: "STM32 XL-density",
    0x416: "STM32 Medium-density ultralow power line",
    0x411: "STM32F2xx",
    0x413: "STM32F4xx",
}


def debug(level, message):
    if QUIET >= level:
        print(message, file=sys.stderr)


class CmdException(Exception):
    pass


class CommandInterface:

    extended_erase = 0

    def __init__(self):
        self.sp = None

    def open(self, a_port='/dev/tty.usbserial-ftCYPMYJ', a_baud_rate=115200):
        self.sp = serial.Serial(
            port=a_port,
            baudrate=a_baud_rate,
            bytesize=8,             # number of write_data bits
            parity=serial.PARITY_EVEN,
            stopbits=1,
            xonxoff=0,              # don't enable software flow control
            rtscts=0,               # don't enable RTS/CTS flow control
            timeout=5               # set a timeout value, None for waiting forever
        )

    def _wait_for_ask(self, info=""):
        # wait for ask
        try:
            ask = ord(self.sp.read())
        except TypeError:
            raise CmdException("Can't read port or timeout")
        else:
            if ask == 0x79:
                # ACK
                return 1
            else:
                if ask == 0x1F:
                    # NACK
                    raise CmdException("NACK "+info)
                else:
                    # Unknown response
                    raise CmdException("Unknown response. "+info+": "+hex(ask))

    def reset(self):
        self.sp.setDTR(0)
        time.sleep(0.1)
        self.sp.setDTR(1)
        time.sleep(0.5)

    def init_chip(self):
        # Set boot
        self.sp.setRTS(0)
        self.reset()

        # Syncro
        self.sp.write("\x7F")
        return self._wait_for_ask("Syncro")

    def release_chip(self):
        self.sp.setRTS(1)
        self.reset()

    def generic(self, command):
        self.sp.write(chr(command))
        # control byte
        self.sp.write(chr(command ^ 0xFF))
        return self._wait_for_ask(hex(command))

    def get(self):
        if not self.generic(0x00):
            raise CmdException("Get (0x00) failed")
        debug(10, "*** Get interface")
        length = ord(self.sp.read())
        version = ord(self.sp.read())
        debug(10, "    Bootloader version: " + hex(version))
        data = [hex(ord(c)) for c in self.sp.read(length)]
        if '0x44' in data:
            self.extended_erase = 1
        debug(10, "    Available commands: " + ", ".join(data))
        self._wait_for_ask("0x00 end")
        return version

    def get_version(self):
        if not self.generic(0x01):
            raise CmdException("GetVersion (0x01) failed")

        debug(10, "*** GetVersion interface")
        version = ord(self.sp.read())
        self.sp.read(2)
        self._wait_for_ask("0x01 end")
        debug(10, "    Bootloader version: " + hex(version))
        return version

    def get_id(self):
        if not self.generic(0x02):
            raise CmdException("GetID (0x02) failed")

        debug(10, "*** GetID interface")
        length = ord(self.sp.read())
        id_data = self.sp.read(length+1)
        self._wait_for_ask("0x02 end")
        _device_id = reduce(lambda x, y: x*0x100+y, map(ord, id_data))
        return _device_id

    @staticmethod
    def _encode_address(address):
        byte3 = (address >> 0) & 0xFF
        byte2 = (address >> 8) & 0xFF
        byte1 = (address >> 16) & 0xFF
        byte0 = (address >> 24) & 0xFF
        crc = byte0 ^ byte1 ^ byte2 ^ byte3
        return chr(byte0) + chr(byte1) + chr(byte2) + chr(byte3) + chr(crc)

    def read_memory(self, address, length):
        assert(length <= 256)
        if not self.generic(0x11):
            raise CmdException("ReadMemory (0x11) failed")

        debug(10, "*** ReadMemory interface")
        self.sp.write(self._encode_address(address))
        self._wait_for_ask("0x11 address failed")
        n = (length - 1) & 0xFF
        crc = n ^ 0xFF
        self.sp.write(chr(n) + chr(crc))
        self._wait_for_ask("0x11 length failed")
        return [ord(c) for c in self.sp.read(length)]

    def go(self, address):
        if not self.generic(0x21):
            raise CmdException("Go (0x21) failed")

        debug(10, "*** Go interface")
        self.sp.write(self._encode_address(address))
        self._wait_for_ask("0x21 go failed")

    def write_memory(self, address, data):
        assert(len(data) <= 256)
        if not self.generic(0x31):
            raise CmdException("Write memory (0x31) failed")

        debug(10, "*** Write memory interface")
        self.sp.write(self._encode_address(address))
        self._wait_for_ask("0x31 address failed")
        length = (len(data)-1) & 0xFF
        debug(10, "    %s bytes to write" % [length + 1])
        self.sp.write(chr(length))  # len really
        crc = 0xFF
        for c in data:
            crc = crc ^ c
            self.sp.write(chr(c))
        self.sp.write(chr(crc))
        self._wait_for_ask("0x31 programming failed")
        debug(10, "    Write memory done")

    def erase_memory(self, sectors=None):
        if self.extended_erase:
            return interface.extended_erase_memory()

        if not self.generic(0x43):
            raise CmdException("Erase memory (0x43) failed")

        debug(10, "*** Erase memory interface")
        if sectors is None:
            # Global erase
            self.sp.write(chr(0xFF))
            self.sp.write(chr(0x00))
        else:
            # Sectors erase
            self.sp.write(chr((len(sectors)-1) & 0xFF))
            crc = 0xFF
            for c in sectors:
                crc = crc ^ c
                self.sp.write(chr(c))
            self.sp.write(chr(crc))
        self._wait_for_ask("0x43 erasing failed")
        debug(10, "    Erase memory done")

    def extended_erase_memory(self):
        if not self.generic(0x44):
            raise CmdException("Extended Erase memory (0x44) failed")

        debug(10, "*** Extended Erase memory interface")
        # Global mass erase
        self.sp.write(chr(0xFF))
        self.sp.write(chr(0xFF))
        # Checksum
        self.sp.write(chr(0x00))
        tmp = self.sp.timeout
        self.sp.timeout = 30
        print("Extended erase (0x44), this can take ten seconds or more")
        self._wait_for_ask("0x44 erasing failed")
        self.sp.timeout = tmp
        debug(10, "    Extended Erase memory done")

    def write_protect(self, sectors):
        if not self.generic(0x63):
            raise CmdException("Write Protect memory (0x63) failed")

        debug(10, "*** Write protect interface")
        self.sp.write(chr((len(sectors)-1) & 0xFF))
        crc = 0xFF
        for c in sectors:
            crc = crc ^ c
            self.sp.write(chr(c))
        self.sp.write(chr(crc))
        self._wait_for_ask("0x63 write protect failed")
        debug(10, "    Write protect done")

    def write_unprotect(self):
        if not self.generic(0x73):
            raise CmdException("Write Unprotect (0x73) failed")

        debug(10, "*** Write Unprotect interface")
        self._wait_for_ask("0x73 write unprotect failed")
        self._wait_for_ask("0x73 write unprotect 2 failed")
        debug(10, "    Write Unprotect done")

    def readout_protect(self):
        if not self.generic(0x82):
            raise CmdException("Readout protect (0x82) failed")

        debug(10, "*** Readout protect interface")
        self._wait_for_ask("0x82 readout protect failed")
        self._wait_for_ask("0x82 readout protect 2 failed")
        debug(10, "    Read protect done")

    def readout_unprotect(self):
        if not self.generic(0x92):
            raise CmdException("Readout unprotect (0x92) failed")

        debug(10, "*** Readout Unprotect interface")
        self._wait_for_ask("0x92 readout unprotect failed")
        self._wait_for_ask("0x92 readout unprotect 2 failed")
        debug(10, "    Read Unprotect done")


# Complex commands section

    def read_memory_data(self, address, length):
        data = []
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
        offs = 0
        while length > 256:
            debug(5, "Write %(len)d bytes at 0x%(address)X" % {'address': address, 'len': 256})
            self.write_memory(address, data[offs:offs + 256])
            offs = offs + 256
            address = address + 256
            length = length - 256
        else:
            debug(5, "Write %(len)d bytes at 0x%(address)X" % {'address': address, 'len': 256})
        self.write_memory(address, data[offs:offs + length] + ([0xFF] * (256 - length)))


def usage():
    print("""Usage: %s [-hqVewvr] [-l length] [-p port] [-b baud] [-a address] [-g address] [file.bin]
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
    -a address  Target address
    -g address  Address to start running at (0x08000000, usually)

    ./stm32loader.py -e -w -v example/main.bin

    """ % sys.argv[0])


if __name__ == "__main__":
    
    # Import Psyco if available
    try:
        import psyco
        psyco.full()
        print("Using Psyco...")
    except ImportError:
        psyco = None
        pass

    configuration = {
        'port': '/dev/tty.usbserial-ftCYPMYJ',
        'baud': 115200,
        'address': 0x08000000,
        'erase': 0,
        'write': 0,
        'verify': 0,
        'read': 0,
        'go_address': -1,
    }

# http://www.python.org/doc/2.5.2/lib/module-getopt.html

    try:
        opts, args = getopt.getopt(sys.argv[1:], "hqVewvrp:b:a:l:g:")
    except getopt.GetoptError as err:
        # print help information and exit:
        # this print something like "option -a not recognized"
        print(str(err))
        usage()
        sys.exit(2)

    QUIET = 5

    for o, a in opts:
        if o == '-V':
            QUIET = 10
        elif o == '-q':
            QUIET = 0
        elif o == '-h':
            usage()
            sys.exit(0)
        elif o == '-e':
            configuration['erase'] = 1
        elif o == '-w':
            configuration['write'] = 1
        elif o == '-v':
            configuration['verify'] = 1
        elif o == '-r':
            configuration['read'] = 1
        elif o == '-p':
            configuration['port'] = a
        elif o == '-b':
            configuration['baud'] = eval(a)
        elif o == '-a':
            configuration['address'] = eval(a)
        elif o == '-g':
            configuration['go_address'] = eval(a)
        elif o == '-l':
            configuration['len'] = eval(a)
        else:
            assert False, "unhandled option"

    interface = CommandInterface()
    interface.open(configuration['port'], configuration['baud'])
    debug(10, "Open port %(port)s, baud %(baud)d" % {'port': configuration['port'], 'baud': configuration['baud']})
    try:
        try:
            interface.init_chip()
        except Exception:
            print("Can't init. Ensure that BOOT0 is enabled and reset device")

        boot_version = interface.get()
        debug(0, "Bootloader version %X" % boot_version)
        device_id = interface.get_id()
        debug(0, "Chip id: 0x%x (%s)" % (device_id, chip_ids.get(device_id, "Unknown")))
#    interface.get_version()
#    interface.get_id()
#    interface.readout_unprotect()
#    interface.write_unprotect()
#    interface.write_protect([0, 1])

        write_data = None

        if configuration['write'] or configuration['verify']:
            write_data = open(args[0], 'rb').read()

        if configuration['erase']:
            interface.erase_memory()

        if configuration['write']:
            interface.write_memory_data(configuration['address'], write_data)

        if configuration['verify']:
            verify = interface.read_memory_data(configuration['address'], len(write_data))
            if write_data == verify:
                print("Verification OK")
            else:
                print("Verification FAILED")
                print(str(len(write_data)) + ' vs ' + str(len(verify)))
                for i in range(0, len(write_data)):
                    if write_data[i] != verify[i]:
                        print(hex(i) + ': ' + hex(write_data[i]) + ' vs ' + hex(verify[i]))

        if not configuration['write'] and configuration['read']:
            read_data = interface.read_memory_data(configuration['address'], configuration['len'])
            open(args[0], 'wb').write(read_data)

        if configuration['go_address'] != -1:
            interface.go(configuration['go_address'])

    finally:
        interface.release_chip()
