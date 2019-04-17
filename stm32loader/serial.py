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
# stm32loader is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.
#
# You should have received a copy of the GNU General Public License
# along with stm32loader; see the file LICENSE.  If not see
# <http://www.gnu.org/licenses/>.

"""
Handle RS-232 serial communication through pyserial.

Offer support for toggling RESET and BOOT0.
"""

import serial


class SerialConnection:
    """Wrap a serial.Serial connection and offer enable_reset and enable_boot0."""

    # pylint: disable=too-many-instance-attributes

    def __init__(self, serial_port, baud_rate=115_200, parity="E"):
        """Construct a SerialConnection (not yet connected)."""
        self.serial_port = serial_port
        self.baud_rate = baud_rate
        self.parity = parity

        # advertise reset / boot0 toggle capability
        self.can_toggle_reset = True
        self.can_toggle_boot0 = True

        self.swap_rts_dtr = False
        self.reset_active_high = False
        self.boot0_active_high = False

        # call connect() to establish connection
        self.serial_connection = None

    def connect(self):
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
            timeout=5,
        )

    def write(self, *args, **kwargs):
        return self.serial_connection.write(*args, **kwargs)

    def read(self, *args, **kwargs):
        return self.serial_connection.read(*args, **kwargs)

    def enable_reset(self, enable=True):
        # reset on the STM32 is active low (0 Volt puts the MCU in reset)
        # but the RS-232 DTR signal is active low by itself, so it inverts this
        # (writing a logical 1 outputs a low voltage == reset enabled)
        level = int(enable)
        if self.reset_active_high:
            level = 1 - level

        if self.swap_rts_dtr:
            self.serial_connection.setRTS(level)
        else:
            self.serial_connection.setDTR(level)

    def enable_boot0(self, enable=True):
        level = int(enable)

        # by default, this is active low
        if not self.boot0_active_high:
            level = 1 - level

        if self.swap_rts_dtr:
            self.serial_connection.setDTR(level)
        else:
            self.serial_connection.setRTS(level)
