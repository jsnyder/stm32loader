#!/usr/bin/env python
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

"""Flash firmware to STM32 microcontrollers over a serial connection."""


from __future__ import print_function

import getopt
import sys

from .bootloader import CHIP_IDS, CommandException, Stm32Bootloader
from .rs232 import SerialConnection

DEFAULT_VERBOSITY = 5


class Stm32Loader:
    """Main application: parse arguments and handle commands."""

    # serial link bit parity, compatible to pyserial serial.PARTIY_EVEN
    PARITY = {"even": "E", "none": "N"}

    def __init__(self):
        """Construct Stm32Loader object with default settings."""
        self.bootloader = None
        self.configuration = {
            "port": "/dev/tty.usbserial-ftCYPMYJ",
            "baud": 115200,
            "parity": self.PARITY["even"],
            "family": None,
            "address": 0x08000000,
            "erase": False,
            "unprotect": False,
            "write": False,
            "verify": False,
            "read": False,
            "go_address": -1,
            "swap_rts_dtr": False,
            "reset_active_high": False,
            "boot0_active_high": False,
            "data_file": None,
        }
        self.verbosity = DEFAULT_VERBOSITY

    def debug(self, level, message):
        """Log a message to stderror if its level is low enough."""
        if self.verbosity >= level:
            print(message, file=sys.stderr)

    def parse_arguments(self, arguments):
        """Parse the list of command-line arguments."""
        # pylint: disable=too-many-branches, eval-used
        try:
            # parse command-line arguments using getopt
            options, arguments = getopt.getopt(arguments, "hqVeuwvrsRBP:p:b:a:l:g:f:", ["help"])
        except getopt.GetoptError as err:
            # print help information and exit:
            # this prints something like "option -a not recognized"
            print(str(err))
            self.print_usage()
            sys.exit(2)

        # if there's a non-named argument left, that's a file name
        if arguments:
            self.configuration["data_file"] = arguments[0]

        for option, value in options:
            if option == "-V":
                self.verbosity = 10
            elif option == "-q":
                self.verbosity = 0
            elif option in ["-h", "--help"]:
                self.print_usage()
                sys.exit(0)
            elif option == "-e":
                self.configuration["erase"] = True
            elif option == "-u":
                self.configuration["unprotect"] = True
            elif option == "-w":
                self.configuration["write"] = True
            elif option == "-v":
                self.configuration["verify"] = True
            elif option == "-r":
                self.configuration["read"] = True
            elif option == "-p":
                self.configuration["port"] = value
            elif option == "-s":
                self.configuration["swap_rts_dtr"] = True
            elif option == "-R":
                self.configuration["reset_active_high"] = True
            elif option == "-B":
                self.configuration["boot0_active_high"] = True
            elif option == "-b":
                self.configuration["baud"] = int(eval(value))
            elif option == "-f":
                self.configuration["family"] = value
            elif option == "-P":
                assert (
                    value.lower() in Stm32Loader.PARITY
                ), "Parity value not recognized: '{0}'.".format(value)
                self.configuration["parity"] = Stm32Loader.PARITY[value.lower()]
            elif option == "-a":
                self.configuration["address"] = int(eval(value))
            elif option == "-g":
                self.configuration["go_address"] = int(eval(value))
            elif option == "-l":
                self.configuration["length"] = int(eval(value))
            else:
                assert False, "unhandled option %s" % option

    def connect(self):
        """Connect to the RS-232 serial port."""
        serial_connection = SerialConnection(
            self.configuration["port"], self.configuration["baud"], self.configuration["parity"]
        )
        self.debug(
            10,
            "Open port %(port)s, baud %(baud)d"
            % {"port": self.configuration["port"], "baud": self.configuration["baud"]},
        )
        try:
            serial_connection.connect()
        except IOError as e:
            print(str(e) + "\n", file=sys.stderr)
            print(
                "Is the device connected and powered correctly?\n"
                "Please use the -p option to select the correct serial port. Examples:\n"
                "  -p COM3\n"
                "  -p /dev/ttyS0\n"
                "  -p /dev/ttyUSB0\n"
                "  -p /dev/tty.usbserial-ftCYPMYJ\n",
                file=sys.stderr,
            )
            exit(1)

        serial_connection.swap_rts_dtr = self.configuration["swap_rts_dtr"]
        serial_connection.reset_active_high = self.configuration["reset_active_high"]
        serial_connection.boot0_active_high = self.configuration["boot0_active_high"]

        self.bootloader = Stm32Bootloader(serial_connection, verbosity=self.verbosity)

        try:
            self.bootloader.reset_from_system_memory()
        except CommandException:
            print("Can't init into bootloader. Ensure that BOOT0 is enabled and reset device.")
            self.bootloader.reset_from_flash()
            sys.exit(1)

    def perform_commands(self):
        """Run all operations as defined by the configuration."""
        # pylint: disable=too-many-branches
        binary_data = None
        if self.configuration["write"] or self.configuration["verify"]:
            with open(self.configuration["data_file"], "rb") as read_file:
                binary_data = bytearray(read_file.read())
        if self.configuration["unprotect"]:
            try:
                self.bootloader.readout_unprotect()
            except CommandException:
                # may be caused by readout protection
                self.debug(0, "Erase failed -- probably due to readout protection")
                self.debug(0, "Quit")
                self.bootloader.reset_from_flash()
                sys.exit(1)
        if self.configuration["erase"]:
            try:
                self.bootloader.erase_memory()
            except CommandException:
                # may be caused by readout protection
                self.debug(
                    0,
                    "Erase failed -- probably due to readout protection\n"
                    "consider using the -u (unprotect) option.",
                )
                self.bootloader.reset_from_flash()
                sys.exit(1)
        if self.configuration["write"]:
            self.bootloader.write_memory_data(self.configuration["address"], binary_data)
        if self.configuration["verify"]:
            read_data = self.bootloader.read_memory_data(
                self.configuration["address"], len(binary_data)
            )
            if binary_data == read_data:
                print("Verification OK")
            else:
                print("Verification FAILED")
                print(str(len(binary_data)) + " vs " + str(len(read_data)))
                for address, data_pair in enumerate(zip(binary_data, read_data)):
                    binary_byte, read_byte = data_pair
                    if binary_byte != read_byte:
                        print(hex(address) + ": " + hex(binary_byte) + " vs " + hex(read_byte))
        if not self.configuration["write"] and self.configuration["read"]:
            read_data = self.bootloader.read_memory_data(
                self.configuration["address"], self.configuration["length"]
            )
            with open(self.configuration["data_file"], "wb") as out_file:
                out_file.write(read_data)
        if self.configuration["go_address"] != -1:
            self.bootloader.go(self.configuration["go_address"])

    def reset(self):
        """Reset the microcontroller."""
        self.bootloader.reset_from_flash()

    @staticmethod
    def print_usage():
        """Print help text explaining the command-line arguments."""
        help_text = """Usage: %s [-hqVeuwvrsRB] [-l length] [-p port] [-b baud] [-P parity]
          [-a address] [-g address] [-f family] [file.bin]
    -e          Erase (note: this is required on previously written memory)
    -u          Unprotect in case erase fails
    -w          Write file content to flash
    -v          Verify flash content versus local file (recommended)
    -r          Read from flash and store in local file
    -l length   Length of read
    -p port     Serial port (default: /dev/tty.usbserial-ftCYPMYJ)
    -b baud     Baudrate (default: 115200)
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

    Example: ./%s -p COM7 -f F1
    Example: ./%s -e -w -v example/main.bin
"""
        current_script = sys.argv[0] if sys.argv else "stm32loader"
        help_text = help_text % (current_script, current_script, current_script)
        print(help_text)

    def read_device_details(self):
        """Show MCU details (bootloader version, chip ID, UID, flash size)."""
        boot_version = self.bootloader.get()
        self.debug(0, "Bootloader version %X" % boot_version)
        device_id = self.bootloader.get_id()
        self.debug(0, "Chip id: 0x%x (%s)" % (device_id, CHIP_IDS.get(device_id, "Unknown")))
        family = self.configuration["family"]
        if not family:
            self.debug(0, "Supply -f [family] to see flash size and device UID, e.g: -f F1")
        else:
            device_uid = self.bootloader.get_uid(family)
            device_uid_string = self.bootloader.format_uid(device_uid)
            self.debug(0, "Device UID: %s" % device_uid_string)

            flash_size = self.bootloader.get_flash_size(family)
            self.debug(0, "Flash size: %d KiB" % flash_size)


def main(*args, **kwargs):
    """
    Parse arguments and execute tasks.

    Default usage is to supply *sys.argv[1:].
    """
    try:
        loader = Stm32Loader()
        loader.parse_arguments(args)
        loader.connect()
        try:
            loader.read_device_details()
            loader.perform_commands()
        finally:
            loader.reset()
    except SystemExit:
        if not kwargs.get("avoid_system_exit", False):
            raise


if __name__ == "__main__":
    main(*sys.argv[1:])
