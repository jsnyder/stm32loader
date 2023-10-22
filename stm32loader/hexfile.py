"""Load binary data from a file in Intel hex format."""

from stm32loader.bootloader import MissingDependencyError

try:
    import intelhex
except ImportError:
    intelhex = None


def load_hex(file_path: str) -> bytes:
    """
    Return bytes from the given hex file.

    Addresses should start at zero and always increment.
    """
    if intelhex is None:
        raise MissingDependencyError(
            "Please install package 'intelhex' in order to read .hex files."
        )

    hex_content = intelhex.IntelHex()
    hex_content.loadhex(str(file_path))
    hex_dict = hex_content.todict()

    addresses = list(hex_dict.keys())
    assert addresses[0] == 0
    assert addresses[-1] == len(addresses) - 1

    return bytes(hex_content.todict().values())
