"""
Tests for the stm32loader executable and main() method.

Several of these tests require an actual STM32 microcontroller to be
connected, and to be programmable (including RESET and BOOT0 toggling).

These hardware tests are disabled by default.
To enable them, configure the device parameters below and
supply the following as argument to pytest:

    -m "hardware"

"""

import os
import subprocess

import pytest

from stm32loader.main import main

HERE = os.path.split(os.path.abspath(__file__))[0]

# Device dependant details
# HyTiny on Windows with FTDI adapter
STM32_CHIP_FAMILY = "F1"
STM32_CHIP_ID = "0x410"
STM32_CHIP_TYPE = "STM32F10x Medium-density"
SERIAL_PORT = "COM7"
# Flaky cable setup, cheap serial adapter...
BAUD_RATE = 9600
KBYTE = 2 ** 10
SIZE = 32 * KBYTE
DUMP_FILE = "dump.bin"
FIRMWARE_FILE = os.path.join(HERE, "../../firmware/generic_boot20_pc13.binary.bin")

# pylint: disable=missing-docstring, redefined-outer-name


@pytest.fixture(scope="module")
def stm32loader():
    def main_with_default_arguments(*args):
        main("-p", SERIAL_PORT, "-b", str(BAUD_RATE), "-q", *args, avoid_system_exit=True)
    return main_with_default_arguments


@pytest.fixture
def dump_file(tmpdir):
    return os.path.join(str(tmpdir), DUMP_FILE)


def test_stm32loader_is_executable():
    subprocess.call(["stm32loader", "--help"])


@pytest.mark.parametrize(
    "help_argument", ["-h", "--help"],
)
def test_argument_h_prints_help_info(help_argument, capsys):
    main(help_argument, avoid_system_exit=True)
    captured = capsys.readouterr()
    assert "Example:" in captured.out


def test_unexisting_serial_port_prints_readable_error(capsys):
    main("-p", "COM108", avoid_system_exit=True)
    captured = capsys.readouterr()
    assert "could not open port 'COM108'" in captured.err
    assert "Is the device connected and powered correctly?" in captured.err


@pytest.mark.hardware
@pytest.mark.missing_hardware
def test_device_not_connected_prints_readable_error(stm32loader, capsys):
    stm32loader()
    captured = capsys.readouterr()
    assert "Can't init into bootloader." in captured.err
    assert "Ensure that BOOT0 is enabled and reset the device." in captured.err


@pytest.mark.hardware
def test_argument_f_prints_chip_id_and_device_type(stm32loader, capsys):
    stm32loader("-f", STM32_CHIP_FAMILY)
    captured = capsys.readouterr()
    assert STM32_CHIP_ID in captured.err
    assert STM32_CHIP_TYPE in captured.err


@pytest.mark.hardware
def test_read_produces_file_of_correct_length(stm32loader, dump_file):
    stm32loader("-r", "-l", "1024", dump_file)
    assert os.stat(dump_file).st_size == 1024


@pytest.mark.hardware
def test_erase_resets_memory_to_all_ones(stm32loader, dump_file):
    # erase
    stm32loader("-e")
    # read all bytes and check if they're 0xFF
    stm32loader("-r", "-l", "1024", dump_file)
    # bytearray() is required for Python 2
    read_data = bytearray(open(dump_file, "rb").read())
    assert all(byte == 0xFF for byte in read_data)


@pytest.mark.hardware
def test_write_saves_correct_data(stm32loader, dump_file):
    # erase and write
    stm32loader("-e", "-w", FIRMWARE_FILE)

    # read and compare data with file on disk
    stm32loader("-r", "-l", str(SIZE), dump_file)
    read_data = open(dump_file, "rb").read()
    original_data = open(FIRMWARE_FILE, "rb").read()

    for address, data in enumerate(zip(read_data, original_data)):
        read_byte, original_byte = data
        assert read_byte == original_byte, "Data mismatch at byte %s: %d vs %d" % (
            address,
            read_byte,
            original_byte,
        )


@pytest.mark.hardware
def test_erase_write_verify_passes(stm32loader):
    stm32loader("-e", "-w", "-v", FIRMWARE_FILE)
