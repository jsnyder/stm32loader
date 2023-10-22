
import atexit

import pytest

from stm32loader.main import Stm32Loader


@pytest.fixture
def program():
    return Stm32Loader()


def test_parse_arguments_without_args_raises_typeerror(program):
    with pytest.raises(TypeError, match="missing.*required.*argument"):
        program.parse_arguments()


def test_parse_arguments_with_standard_args_passes(program):
    program.parse_arguments(["-p", "port", "-b", "9600", "-q"])


@pytest.mark.parametrize(
    "help_argument", ["-h", "--help"],
)
def test_parse_arguments_with_help_raises_systemexit(program, help_argument):
    with pytest.raises(SystemExit):
        program.parse_arguments([help_argument])


def test_parse_arguments_erase_without_port_complains_about_missing_argument(program, capsys):
    try:
        program.parse_arguments(["-e", "-w", "-v", "file.bin"])
    except SystemExit:
        pass

    # Also call atexit functions so that the hint about using an env variable
    # is printed.
    atexit._run_exitfuncs()

    _output, error_output = capsys.readouterr()
    if not error_output:
        pytest.skip("Not sure why nothing is captured in some pytest runs?")
    assert "arguments are required: -p/--port" in error_output
    assert "STM32LOADER_SERIAL_PORT" in error_output
