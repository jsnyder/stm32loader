"""
Tests for the stm32loader.bootloader.

Several of these tests require an actual STM32 microcontroller to be
connected, and to be programmable (including RESET and BOOT0 toggling).

These hardware tests are disabled by default.
To enable them, configure the device parameters below and
supply the following as argument to pytest:

    -m "hardware"

"""

from stm32loader.bootloader import Stm32Bootloader
from stm32loader.uart import SerialConnection

import pytest

SERIAL_PORT = "COM7"
BAUD_RATE = 9600

# pylint: disable=missing-docstring, redefined-outer-name


@pytest.fixture
def serial_connection():
    serial_connection = SerialConnection(SERIAL_PORT, BAUD_RATE)
    serial_connection.connect()
    return serial_connection


@pytest.fixture
def stm32(serial_connection):
    stm32 = Stm32Bootloader(serial_connection)
    return stm32


@pytest.mark.hardware
def test_erase_with_page_erases_only_that_page(stm32):
    stm32.reset_from_system_memory()
    base = 0x08000000
    before, middle, after = base + 0, base + 256, base + 512

    # erase full device
    stm32.erase_memory()

    # check that erase was successful
    assert all(byte == 0xFF for byte in stm32.read_memory(before, 16))
    assert all(byte == 0xFF for byte in stm32.read_memory(middle, 16))
    assert all(byte == 0xFF for byte in stm32.read_memory(after, 16))

    # write zeros to three pages (and verify success)
    stm32.write_memory(before, bytearray([0x00] * 16))
    stm32.write_memory(middle, bytearray([0x00] * 16))
    stm32.write_memory(after, bytearray([0x00] * 16))
    assert all(byte == 0x00 for byte in stm32.read_memory(before, 16))
    assert all(byte == 0x00 for byte in stm32.read_memory(middle, 16))
    assert all(byte == 0x00 for byte in stm32.read_memory(after, 16))

    # erase only the middle page
    stm32.erase_memory(pages=[0])

    # check that middle page is erased, others are not
    assert all(byte == 0x00 for byte in stm32.read_memory(before, 16))
    assert all(byte == 0xFF for byte in stm32.read_memory(middle, 256))
    assert all(byte == 0x00 for byte in stm32.read_memory(after, 16))

