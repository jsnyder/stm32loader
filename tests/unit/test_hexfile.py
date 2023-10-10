
from pathlib import Path

HERE = Path(__file__).parent
DATA = HERE / "../data"


from stm32loader.hexfile import load_hex


def test_load_hex_delivers_bytes():
    small_hex_path = DATA / "small.hex"
    data = load_hex(small_hex_path)
    assert data == bytes(range(16))
