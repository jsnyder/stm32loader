"""Unit tests for the Stm32Loader class."""

import pytest

from unittest.mock import MagicMock

from stm32loader import bootloader as Stm32
from stm32loader.bootloader import Stm32Bootloader

# pylint: disable=missing-docstring, redefined-outer-name


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
    with pytest.raises(Stm32.CommandError, match="custom message"):
        bootloader.write_and_ack("custom message", 0x00)


def test_write_memory_with_length_higher_than_256_raises_data_length_error(bootloader):
    with pytest.raises(Stm32.DataLengthError, match=r"Can not write more than 256 bytes at once\."):
        bootloader.write_memory(0, [1] * 257)


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


def test_read_memory_with_length_higher_than_256_raises_data_length_error(bootloader):
    with pytest.raises(Stm32.DataLengthError, match=r"Can not read more than 256 bytes at once\."):
        bootloader.read_memory(0, length=257)


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


def test_erase_memory_without_pages_sends_global_erase(bootloader, write):
    bootloader.erase_memory()
    assert write.data_was_written(b'\xff\x00')


def test_erase_memory_with_pages_sends_sector_count(bootloader, write):
    bootloader.erase_memory([0x11, 0x12, 0x13, 0x14])
    assert write.data_was_written(b'\x03')


def test_erase_memory_with_pages_sends_sector_addresses_with_checksum(bootloader, write):
    bootloader.erase_memory([0x01, 0x02, 0x04, 0x08])
    print(write.written_data)
    assert write.data_was_written(b'\x01\x02\x04\x08\x0c')


def test_erase_memory_with_page_count_higher_than_255_raises_page_index_error(bootloader):
    with pytest.raises(Stm32.PageIndexError, match="Can not erase more than 255 pages at once."):
        bootloader.erase_memory([1] * 256)


def test_erase_memory_family_l0_without_pages_erases_individual_pages(connection, write):
    bootloader = Stm32Bootloader(connection, device_family="L0")
    bootloader.command = MagicMock()
    bootloader.get_flash_size_and_uid = MagicMock()
    bootloader.get_flash_size_and_uid.return_value = (16, 0x01)
    bootloader.erase_memory()

    # Page count - 1.
    assert write.written_data[0] == 127
    # Pages.
    assert write.written_data[1:3] == b'\x00\x01'
    # Length: command + byte count + page-addresses + CRC
    assert len(write.written_data) == 130


def test_extended_erase_memory_without_pages_sends_global_mass_erase(bootloader, write):
    bootloader.extended_erase_memory()
    assert write.data_was_written(b'\xff\xff\x00')


def test_extended_erase_memory_with_page_count_higher_than_65535_raises_page_index_error(bootloader):
    with pytest.raises(Stm32.PageIndexError, match="Can not erase more than 65535 pages at once."):
        bootloader.extended_erase_memory([1] * 65536)


def test_extended_erase_memory_with_pages_sends_two_byte_sector_count(bootloader, write):
    bootloader.extended_erase_memory([0x11, 0x12, 0x13, 0x14])
    assert write.data_was_written(b'\x00\x03')


def test_extended_erase_memory_with_pages_sends_two_byte_sector_addresses_with_single_byte_checksum(bootloader, write):
    bootloader.extended_erase_memory([0x01, 0x02, 0x04, 0x0ff0])
    assert write.data_was_written(b'\x00\x01\x00\x02\x00\x04\x0f\xf0\xfb')


def test_write_protect_sends_page_addresses_and_checksum(bootloader, write):
    bootloader.write_protect([0x01, 0x08])
    assert write.data_was_written(b'\x01\x08\x08')


def test_verify_data_with_identical_data_passes():
    Stm32Bootloader.verify_data(b'\x05', b'\x05')


def test_verify_data_with_different_byte_count_raises_verify_error_complaining_about_length_difference():
    with pytest.raises(Stm32.DataMismatchError, match=r"Data length does not match.*2.*vs.*1.*bytes"):
        Stm32Bootloader.verify_data(b'\x05\x06', b'\x01')


def test_verify_data_with_non_identical_data_raises_verify_error_complaining_about_mismatched_byte():
    with pytest.raises(Stm32.DataMismatchError, match=r"Verification data does not match read data.*mismatch.*0x1.*0x6.*0x7"):
        Stm32Bootloader.verify_data(b'\x05\x06', b'\x05\x07')


@pytest.mark.parametrize(
    "family", ["F1", "F3", "F7"],
)
def test_get_uid_for_known_family_reads_at_correct_address(connection, family):
    bootloader = Stm32Bootloader(connection, device_family=family)
    bootloader.read_memory = MagicMock()
    bootloader.get_uid()
    uid_address = bootloader.UID_ADDRESS[family]
    assert bootloader.read_memory.called_once_with(uid_address)


def test_get_uid_for_family_without_uid_returns_uid_not_supported(connection):
    bootloader = Stm32Bootloader(connection, device_family="F0")
    assert bootloader.UID_NOT_SUPPORTED == bootloader.get_uid()


def test_get_uid_for_unknown_family_returns_uid_address_unknown(connection):
    bootloader = Stm32Bootloader(connection, device_family="X")
    assert bootloader.UID_ADDRESS_UNKNOWN == bootloader.get_uid()


@pytest.mark.parametrize(
    "family", ["F4", "L0"],
)
def test_get_flash_size_and_uid_for_exception_families_returns_size_and_uid(connection, family):
    bootloader = Stm32Bootloader(connection, device_family=family)
    bootloader.read_memory = MagicMock()

    memory_block = bytearray([0] * 256)

    # Set up the 'UID' value (12 bytes)
    # and flash_size value (2 bytes).
    uid_address = bootloader.UID_ADDRESS[family] & 0xFF
    memory_block[uid_address: uid_address + 12] = b'\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c'
    flash_size_address = bootloader.FLASH_SIZE_ADDRESS[family] & 0xFF
    memory_block[flash_size_address: flash_size_address + 2] = b'\x01\x02'
    bootloader.read_memory.return_value = memory_block

    flash_size, uid = bootloader.get_flash_size_and_uid()

    assert flash_size == 0x0201
    assert uid == b'\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c'


@pytest.mark.parametrize(
    "uid_string",
    [
        (0, "UID not supported in this part"),
        (-1, "UID address unknown"),
        (bytearray(b"\x12\x34\x56\x78\x9a\xbc\xde\x01\x12\x34\x56\x78"), "3412-7856-01DEBC9A-78563412"),
    ],
)
def test_format_uid_returns_correct_string(bootloader, uid_string):
    uid, expected_description = uid_string
    description = bootloader.format_uid(uid)
    assert description == expected_description
