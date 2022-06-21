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


import argparse
import atexit
import copy
import os
import sys
from types import SimpleNamespace

try:
    from progress.bar import ChargingBar as progress_bar
except ImportError:
    progress_bar = None

from stm32loader import __version__, bootloader
from stm32loader.uart import SerialConnection

DEFAULT_VERBOSITY = 5


class HelpFormatter(argparse.RawDescriptionHelpFormatter, argparse.ArgumentDefaultsHelpFormatter):
    """Custom help formatter -- don't print confusing default values."""

    def _get_help_string(self, action):
        action = copy.copy(action)
        # Don't show "(default: None)" for arguments without defaults,
        # or "(default: False)" for boolean flags, and hide the
        # (default: 5) from --verbose's help because it's confusing.
        if not action.default or action.dest == "verbosity":
            action.default = argparse.SUPPRESS
        return super()._get_help_string(action)

    def _format_actions_usage(self, actions, groups):
        # Always treat -p/--port as required. See the note about the
        # argparse hack in Stm32Loader.parse_arguments for why.
        def tweak_action(action):
            action = copy.copy(action)
            if action.dest == "port":
                action.required = True
            return action

        return super()._format_actions_usage(map(tweak_action, actions), groups)


class Stm32Loader:
    """Main application: parse arguments and handle commands."""

    # serial link bit parity, compatible to pyserial serial.PARTIY_EVEN
    PARITY = {"even": "E", "none": "N"}

    def __init__(self):
        """Construct Stm32Loader object with default settings."""
        self.stm32 = None
        self.configuration = SimpleNamespace()

    def debug(self, level, message):
        """Log a message to stderror if its level is low enough."""
        if self.configuration.verbosity >= level:
            print(message, file=sys.stderr)

    def parse_arguments(self, arguments):
        """Parse the list of command-line arguments."""
        parser = argparse.ArgumentParser(
            prog="stm32loader",
            description="Flash firmware to STM32 microcontrollers.",
            epilog="\n".join(
                [
                    "examples:",
                    "  %(prog)s -p COM7 -f F1",
                    "  %(prog)s -e -w -v example/main.bin",
                ]
            ),
            formatter_class=HelpFormatter,
        )

        data_file_arg = parser.add_argument(
            "data_file",
            metavar="FILE.BIN",
            type=str,
            nargs="?",
            help="File to read from or store to flash.",
        )

        parser.add_argument(
            "-e",
            "--erase",
            action="store_true",
            help="Erase (note: this is required on previously written memory).",
        )

        parser.add_argument(
            "-u", "--unprotect", action="store_true", help="Unprotect in case erase fails."
        )

        parser.add_argument(
            "-w", "--write", action="store_true", help="Write file content to flash."
        )

        parser.add_argument(
            "-v",
            "--verify",
            action="store_true",
            help="Verify flash content versus local file (recommended).",
        )

        parser.add_argument(
            "-r", "--read", action="store_true", help="Read from flash and store in local file."
        )

        length_arg = parser.add_argument(
            "-l", "--length", action="store", type=int, help="Length of read."
        )

        default_port = os.environ.get("STM32LOADER_SERIAL_PORT")
        port_arg = parser.add_argument(
            "-p",
            "--port",
            action="store",
            type=str,  # morally required=True
            default=default_port,
            help=(
                "Serial port" + ("." if default_port else " (default: $STM32LOADER_SERIAL_PORT).")
            ),
        )

        parser.add_argument(
            "-b", "--baud", action="store", type=int, default=115200, help="Baudrate."
        )

        address_arg = parser.add_argument(
            "-a", "--address", action="store", type=int, default=0x08000000, help="Target address."
        )

        parser.add_argument(
            "-g",
            "--go-address",
            action="store",
            type=int,
            metavar="ADDRESS",
            help="Start executing from address (0x08000000, usually).",
        )

        default_family = os.environ.get("STM32LOADER_FAMILY")
        parser.add_argument(
            "-f",
            "--family",
            action="store",
            type=str,
            default=default_family,
            help=(
                "Device family to read out device UID and flash size; "
                "e.g F1 for STM32F1xx"
                + ("." if default_family else " (default: $STM32LOADER_FAMILY).")
            ),
        )

        parser.add_argument(
            "-V",
            "--verbose",
            dest="verbosity",
            action="store_const",
            const=10,
            default=DEFAULT_VERBOSITY,
            help="Verbose mode.",
        )

        parser.add_argument(
            "-q", "--quiet", dest="verbosity", action="store_const", const=0, help="Quiet mode."
        )

        parser.add_argument(
            "-s",
            "--swap-rts-dtr",
            action="store_true",
            help="Swap RTS and DTR: use RTS for reset and DTR for boot0.",
        )

        parser.add_argument(
            "-R", "--reset-active-high", action="store_true", help="Make RESET active high."
        )

        parser.add_argument(
            "-B", "--boot0-active-low", action="store_true", help="Make BOOT0 active low."
        )

        parser.add_argument(
            "-n", "--no-progress", action="store_true", help="Don't show progress bar."
        )

        parser.add_argument(
            "-P",
            "--parity",
            action="store",
            type=str,
            default="even",
            choices=self.PARITY.keys(),
            help='Parity: "even" for STM32, "none" for BlueNRG.',
        )

        parser.add_argument("--version", action="version", version=__version__)

        # Hack: We want certain arguments to be required when one
        # of -rwv is specified, but argparse doesn't support
        # conditional dependencies like that. Instead, we add the
        # requirements post-facto and re-run the parse to get the error
        # messages we want. A better solution would be to use
        # subcommands instead of options for -rwv, but this would
        # change the command-line interface.
        #
        # We also use this gross hack to provide a hint about the
        # STM32LOADER_SERIAL_PORT environment variable when -p
        # is omitted; we only set --port as required after the first
        # parse so we can hook in a custom error message.

        self.configuration = parser.parse_args(arguments)

        if not self.configuration.port:
            port_arg.required = True
            atexit.register(
                lambda: print(
                    "{}: note: you can also set the environment "
                    "variable STM32LOADER_SERIAL_PORT".format(parser.prog),
                    file=sys.stderr,
                )
            )

        if self.configuration.read or self.configuration.write or self.configuration.verify:
            data_file_arg.nargs = None
            data_file_arg.required = True

        if self.configuration.read:
            length_arg.required = True
            address_arg.required = True

        parser.parse_args(arguments)

        # parse successful, process options further
        self.configuration.parity = Stm32Loader.PARITY[self.configuration.parity.lower()]

    def connect(self):
        """Connect to the bootloader UART over an RS-232 serial port."""
        serial_connection = SerialConnection(
            self.configuration.port, self.configuration.baud, self.configuration.parity
        )
        self.debug(
            10,
            "Open port %(port)s, baud %(baud)d"
            % {"port": self.configuration.port, "baud": self.configuration.baud},
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
            sys.exit(1)

        serial_connection.swap_rts_dtr = self.configuration.swap_rts_dtr
        serial_connection.reset_active_high = self.configuration.reset_active_high
        serial_connection.boot0_active_low = self.configuration.boot0_active_low

        show_progress = self._get_progress_bar(self.configuration.no_progress)

        self.stm32 = bootloader.Stm32Bootloader(
            serial_connection, verbosity=self.configuration.verbosity, show_progress=show_progress
        )

        try:
            print("Activating bootloader (select UART)")
            self.stm32.reset_from_system_memory()
        except bootloader.CommandError:
            print(
                "Can't init into bootloader. Ensure that BOOT0 is enabled and reset the device.",
                file=sys.stderr,
            )
            self.stm32.reset_from_flash()
            sys.exit(1)

    def perform_commands(self):
        """Run all operations as defined by the configuration."""
        # pylint: disable=too-many-branches
        binary_data = None
        if self.configuration.write or self.configuration.verify:
            with open(self.configuration.data_file, "rb") as read_file:
                binary_data = bytearray(read_file.read())
        if self.configuration.unprotect:
            try:
                self.stm32.readout_unprotect()
            except bootloader.CommandError:
                # may be caused by readout protection
                self.debug(0, "Erase failed -- probably due to readout protection")
                self.debug(0, "Quit")
                self.stm32.reset_from_flash()
                sys.exit(1)
        if self.configuration.erase:
            try:
                self.stm32.erase_memory()
            except bootloader.CommandError:
                # may be caused by readout protection
                self.debug(
                    0,
                    "Erase failed -- probably due to readout protection\n"
                    "consider using the -u (unprotect) option.",
                )
                self.stm32.reset_from_flash()
                sys.exit(1)
        if self.configuration.write:
            self.stm32.write_memory_data(self.configuration.address, binary_data)
        if self.configuration.verify:
            read_data = self.stm32.read_memory_data(self.configuration.address, len(binary_data))
            try:
                bootloader.Stm32Bootloader.verify_data(read_data, binary_data)
                print("Verification OK")
            except bootloader.DataMismatchError as e:
                print("Verification FAILED: %s" % e, file=sys.stdout)
                sys.exit(1)
        if not self.configuration.write and self.configuration.read:
            read_data = self.stm32.read_memory_data(
                self.configuration.address, self.configuration.length
            )
            with open(self.configuration.data_file, "wb") as out_file:
                out_file.write(read_data)
        if self.configuration.go_address is not None:
            self.stm32.go(self.configuration.go_address)

    def reset(self):
        """Reset the microcontroller."""
        self.stm32.reset_from_flash()

    def read_device_id(self):
        """Show chip ID and bootloader version."""
        boot_version = self.stm32.get()
        self.debug(0, "Bootloader version: 0x%X" % boot_version)
        device_id = self.stm32.get_id()
        self.debug(
            0, "Chip id: 0x%X (%s)" % (device_id, bootloader.CHIP_IDS.get(device_id, "Unknown"))
        )

    def read_device_uid(self):
        """Show chip UID and flash size."""
        family = self.configuration.family
        if not family:
            self.debug(0, "Supply -f [family] to see flash size and device UID, e.g: -f F1")
            return

        try:
            if family not in ["F4", "L0"]:
                flash_size = self.stm32.get_flash_size()
                device_uid = self.stm32.get_uid()
            else:
                # special fix for F4 and L0 devices
                flash_size, device_uid = self.stm32.get_flash_size_and_uid()
        except bootloader.CommandError as e:
            self.debug(
                0,
                "Something was wrong with reading chip family data: " + str(e),
            )
            return

        device_uid_string = self.stm32.format_uid(device_uid)
        self.debug(0, "Device UID: %s" % device_uid_string)
        self.debug(0, "Flash size: %d KiB" % flash_size)

    @staticmethod
    def _get_progress_bar(no_progress=False):
        if no_progress or not progress_bar:
            return None

        return bootloader.ShowProgress(progress_bar)


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
            loader.read_device_id()
            loader.read_device_uid()
            loader.perform_commands()
        finally:
            loader.reset()
    except SystemExit:
        if not kwargs.get("avoid_system_exit", False):
            raise


if __name__ == "__main__":
    main(*sys.argv[1:])
