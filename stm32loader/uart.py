# Author: Floris Lambrechts
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

"""
Handle RS-232 serial communication through pyserial.

Offer support for toggling RESET and BOOT0.
"""

# not naming this file itself 'serial', because that name-clashes in Python 2
import serial


class SerialConnection(object):
    """Wrap a serial.Serial connection and toggle reset and boot0."""

    # Note: inheriting from object is required for Python2 setters
    # https://stackoverflow.com/questions/598077/why-does-foo-setter-in-python-not-work-for-me

    # pylint: disable=too-many-instance-attributes

    def __init__(self, serial_port, baud_rate=115200, parity="E"):
        """Construct a SerialConnection (not yet connected)."""
        self.serial_port = serial_port
        self.baud_rate = baud_rate
        self.parity = parity

        self.swap_rts_dtr = False
        self.reset_active_high = False
        self.boot0_active_low = False

        # don't connect yet; caller should use connect() separately
        self.serial_connection = None

        self._timeout = 5

    @property
    def timeout(self):
        """Get timeout."""
        return self._timeout

    @timeout.setter
    def timeout(self, timeout):
        """Set timeout."""
        self._timeout = timeout
        self.serial_connection.timeout = timeout

    def connect(self):
        """Connect to the UART serial port."""
        self.serial_connection = serial.Serial(
            port=self.serial_port,
            baudrate=self.baud_rate,
            # number of write_data bits
            bytesize=8,
            parity=self.parity,
            stopbits=1,
            # don't enable software flow control
            xonxoff=0,
            # don't enable RTS/CTS flow control
            rtscts=0,
            # set a timeout value, None for waiting forever
            timeout=self._timeout,
        )

    def write(self, *args, **kwargs):
        """Write the given data to the serial connection."""
        return self.serial_connection.write(*args, **kwargs)

    def read(self, *args, **kwargs):
        """Read the given amount of bytes from the serial connection."""
        return self.serial_connection.read(*args, **kwargs)

    def enable_reset(self, enable=True):
        """Enable or disable the reset IO line."""
        # reset on the STM32 is active low (0 Volt puts the MCU in reset)
        # but the RS-232 modem control DTR and RTS signals are active low
        # themselves, so these get inverted -- writing a logical 1 outputs
        # a low voltage, i.e. enables reset)
        level = int(enable)
        if self.reset_active_high:
            level = 1 - level

        if self.swap_rts_dtr:
            self.serial_connection.setRTS(level)
        else:
            self.serial_connection.setDTR(level)

    def enable_boot0(self, enable=True):
        """Enable or disable the boot0 IO line."""
        level = int(enable)

        # by default, this is active high
        if not self.boot0_active_low:
            level = 1 - level

        if self.swap_rts_dtr:
            self.serial_connection.setDTR(level)
        else:
            self.serial_connection.setRTS(level)
