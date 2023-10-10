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


import sys
from types import SimpleNamespace
from pathlib import Path

try:
    from progress.bar import ChargingBar as progress_bar
except ImportError:
    progress_bar = None

from stm32loader import args
from stm32loader import hexfile
from stm32loader import bootloader
from stm32loader.uart import SerialConnection


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
        self.configuration = args.parse_arguments(arguments)

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
            serial_connection,
            verbosity=self.configuration.verbosity,
            show_progress=show_progress,
            device_family=self.configuration.family,
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
            data_file_path = Path(self.configuration.data_file)
            if data_file_path.suffix == ".hex":
                binary_data = hexfile.load_hex(data_file_path)
            else:
                binary_data = data_file_path.read_bytes()
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
        family = self.configuration.family
        if family == "NRG":
            # ST AN4872.
            # Three bytes encode metal fix, mask set,
            # BlueNRG-series + flash size.
            metal_fix = (device_id & 0xFF0000) >> 16
            mask_set = (device_id & 0x00FF00) >> 8
            device_id = device_id & 0x0000FF
            self.debug(0, "Metal fix: 0x%X" % metal_fix)
            self.debug(0, "Mask set: 0x%X" % mask_set)

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


def main(*arguments, **kwargs):
    """
    Parse arguments and execute tasks.

    Default usage is to supply *sys.argv[1:].
    """
    try:
        loader = Stm32Loader()
        loader.parse_arguments(arguments)
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
