"""Unit tests for the Stm32Loader class."""

import pytest

from stm32loader.bootloader import CommandException, Stm32Bootloader

try:
    from unittest.mock import MagicMock
except ImportError:
    # Python version <= 3.2
    from mock import MagicMock

#pylint: disable=missing-docstring, redefined-outer-name

@pytest.fixture
def connection():
    connection = MagicMock()
    connection.read.return_value = [Stm32Bootloader.Reply.ACK]
    return connection


@pytest.fixture
def write(connection):
    connection.write.written_data = bytearray()

    def log_written_data(data):
        connection.write.written_data.extend(data)

    def data_was_written(data):
        return data in connection.write.written_data

    connection.write.data_was_written = data_was_written
    connection.write.side_effect = log_written_data
    return connection.write


@pytest.fixture
def bootloader(connection):
    return Stm32Bootloader(connection)


def test_constructor_with_connection_none_passes():
    Stm32Bootloader(connection=None)


def test_constructor_does_not_use_connection_directly(connection):
    Stm32Bootloader(connection)
    assert not connection.method_calls


def test_write_without_data_sends_no_bytes(bootloader, write):
    bootloader.write()
    assert not write.written_data


def test_write_with_bytes_sends_bytes_verbatim(bootloader, write):
    bootloader.write(b'\x00\x11')
    assert write.data_was_written(b'\x00\x11')


def test_write_with_integers_sends_integers_as_bytes(bootloader, write):
    bootloader.write(0x03, 0x0a)
    assert write.data_was_written(b'\x03\x0a')


def test_write_and_ack_with_nack_response_raises_commandexception(bootloader):
    bootloader.connection.read = MagicMock()
    bootloader.connection.read.return_value = [Stm32Bootloader.Reply.NACK]
    with pytest.raises(CommandException, match="custom message"):
        bootloader.write_and_ack("custom message", 0x00)


def test_write_memory_with_zero_bytes_does_not_send_anything(bootloader, connection):
    bootloader.write_memory(0, b"")
    assert not connection.method_calls


def test_write_memory_with_single_byte_sends_four_data_bytes_padded_with_0xff(bootloader, write):
    bootloader.write_memory(0, b"1")
    assert write.data_was_written(b"1\xff\xff\xff")


def test_write_memory_sends_correct_number_of_bytes(bootloader, write):
    bootloader.write_memory(0, bytearray([0] * 4))
    # command byte, control byte, 4 address bytes, address checksum,
    # length byte, 4 data bytes, checksum byte
    byte_count = 2 + 4 + 1 + 1 + 4 + 1
    assert len(write.written_data) == byte_count


def test_read_memory_sends_address_with_checksum(bootloader, write):
    bootloader.read_memory(0x0f, 4)
    assert write.data_was_written(b'\x00\x00\x00\x0f\x0f')


def test_read_memory_sends_length_with_checksum(bootloader, write):
    bootloader.read_memory(0, 0x0f + 1)
    assert write.data_was_written(b'\x0f\xf0')


def test_command_sends_command_and_control_bytes(bootloader, write):
    bootloader.command(0x01, "bogus command")
    assert write.data_was_written(b"\x01\xfe")


def test_reset_from_system_memory_sends_command_synchronize(bootloader, write):
    bootloader.reset_from_system_memory()
    synchro_command = Stm32Bootloader.Command.SYNCHRONIZE
    assert write.data_was_written(bytearray([synchro_command]))


def test_encode_address_returns_correct_bytes_with_checksum():
    # pylint:disable=protected-access
    encoded_address = Stm32Bootloader._encode_address(0x04030201)
    assert bytes(encoded_address) == b"\x04\x03\x02\x01\x04"


def test_erase_memory_without_sectors_sends_global_erase(bootloader, write):
    bootloader.erase_memory()
    assert write.data_was_written(b'\xff\x00')


def test_erase_memory_with_sectors_sends_sector_addresses_with_(bootloader, write):
    bootloader.erase_memory([0x01, 0x02, 0x04, 0x08])
    assert write.data_was_written(b'\x01\x02\x04\x08\x0b')


def test_extended_erase_memory_sends_global_mass_erase(bootloader, write):
    bootloader.extended_erase_memory()
    assert write.data_was_written(b'\xff\xff\x00')


def test_write_protect_sends_page_addresses_and_checksum(bootloader, write):
    bootloader.write_protect([0x01, 0x08])
    assert write.data_was_written(b'\x01\x08\x08')
