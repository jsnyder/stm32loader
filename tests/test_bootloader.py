
from stm32loader.bootloader import Stm32Bootloader

import pytest

try:
    from unittest.mock import MagicMock
except ImportError:
    # Python version <= 3.2
    from mock import MagicMock


@pytest.fixture
def connection():
    connection = MagicMock()
    connection.read.return_value = [Stm32Bootloader.Reply.ACK]
    return connection


@pytest.fixture
def write(connection):
    def write_called_with_data(data):
        data_call = (bytearray(data), )
        return 1 == sum(args[0] == data_call for args in connection.write.call_args_list)
    connection.write.called_with_data = write_called_with_data
    return connection.write


@pytest.fixture
def bootloader(connection):
    return Stm32Bootloader(connection)


def test_constructor_with_connection_None_passes():
    Stm32Bootloader(connection=None)


def test_constructor_does_not_use_connection_directly(connection):
    Stm32Bootloader(connection)
    assert not connection.method_calls


def test_write_memory_with_zero_bytes_does_not_send_anything(bootloader, connection):
    bootloader.write_memory(0, b'')
    assert not connection.method_calls


def test_write_memory_with_single_byte_sends_four_data_bytes_padded_with_0xff(bootloader, write):
    bootloader.write_memory(0, b'1')
    assert write.called_with_data(b'1\xff\xff\xff')


def test_encode_address_returns_correct_bytes_with_checksum():
    encoded_address = Stm32Bootloader._encode_address(0x04030201)
    assert bytes(encoded_address) == b'\x04\x03\x02\x01\x04'
