"""Parse command-line arguments."""

import argparse
import atexit
import copy
import os
import sys

from stm32loader import __version__


DEFAULT_VERBOSITY = 5


class HelpFormatter(argparse.RawDescriptionHelpFormatter, argparse.ArgumentDefaultsHelpFormatter):
    """Custom help formatter -- don't print confusing default values."""

    def _get_help_string(self, action):
        action = copy.copy(action)
        # Don't show "(default: None)" for arguments without defaults,
        # or "(default: False)" for boolean flags, and hide the
        # (default: 5) from --verbose's help because it's confusing.
        if not action.default or action.dest == "verbosity":
            action.default = argparse.SUPPRESS
        return super()._get_help_string(action)

    def _format_actions_usage(self, actions, groups):
        # Always treat -p/--port as required. See the note about the
        # argparse hack in Stm32Loader.parse_arguments for why.
        def tweak_action(action):
            action = copy.copy(action)
            if action.dest == "port":
                action.required = True
            return action

        return super()._format_actions_usage(map(tweak_action, actions), groups)


def _auto_int(x):
    """Convert to int with automatic base detection."""
    # This supports 0x10 == 16 and 10 == 10
    return int(x, 0)


def parse_arguments(arguments):
    """Parse the given command-line arguments and return the configuration."""

    parser = argparse.ArgumentParser(
        prog="stm32loader",
        description="Flash firmware to STM32 microcontrollers.",
        epilog="\n".join(
            [
                "examples:",
                "  %(prog)s --port COM7 --family F1",
                "  %(prog)s --erase --write --verify example/main.bin",
            ]
        ),
        formatter_class=HelpFormatter,
    )

    data_file_arg = parser.add_argument(
        "data_file",
        metavar="FILE.BIN",
        type=str,
        nargs="?",
        help="File to read from or store to flash.",
    )

    parser.add_argument(
        "-e",
        "--erase",
        action="store_true",
        help=(
            "Erase the full flash memory or a specific region (support --address and --length)."
            " Note: this is required on previously written memory.",
        )
    )

    parser.add_argument(
        "-u", "--unprotect", action="store_true", help="Unprotect flash from readout."
    )

    parser.add_argument(
        "-x", "--protect", action="store_true", help="Protect flash against readout."
    )

    parser.add_argument("-w", "--write", action="store_true", help="Write file content to flash.")

    parser.add_argument(
        "-v",
        "--verify",
        action="store_true",
        help="Verify flash content versus local file (recommended).",
    )

    parser.add_argument(
        "-r", "--read", action="store_true", help="Read from flash and store in local file."
    )

    length_arg = parser.add_argument(
        "-l", "--length", action="store", type=_auto_int, help="Length of read or erase."
    )

    default_port = os.environ.get("STM32LOADER_SERIAL_PORT")
    port_arg = parser.add_argument(
        "-p",
        "--port",
        action="store",
        type=str,  # morally required=True
        default=default_port,
        help=("Serial port" + ("." if default_port else " (default: $STM32LOADER_SERIAL_PORT).")),
    )

    parser.add_argument(
        "-b", "--baud", action="store", type=int, default=115200, help="Baudrate."
    )

    address_arg = parser.add_argument(
        "-a",
        "--address",
        action="store",
        type=_auto_int,
        default=0x08000000,
        help="Target address for read or write. For erase, this is used when you supply --length.",
    )

    parser.add_argument(
        "-g",
        "--go-address",
        action="store",
        type=_auto_int,
        metavar="ADDRESS",
        help="Start executing from address (0x08000000, usually).",
    )

    default_family = os.environ.get("STM32LOADER_FAMILY")
    parser.add_argument(
        "-f",
        "--family",
        action="store",
        type=str,
        default=default_family,
        help=(
            "Device family to read out device UID and flash size; "
            "e.g F1 for STM32F1xx. Possible values: F0, F1, F3, F4, F7, H7, L4, L0, G0, NRG."
            + ("." if default_family else " (default: $STM32LOADER_FAMILY).")
        ),
    )

    parser.add_argument(
        "-V",
        "--verbose",
        dest="verbosity",
        action="store_const",
        const=10,
        default=DEFAULT_VERBOSITY,
        help="Verbose mode.",
    )

    parser.add_argument(
        "-q", "--quiet", dest="verbosity", action="store_const", const=0, help="Quiet mode."
    )

    parser.add_argument(
        "-s",
        "--swap-rts-dtr",
        action="store_true",
        help="Swap RTS and DTR: use RTS for reset and DTR for boot0.",
    )

    parser.add_argument(
        "-R", "--reset-active-high", action="store_true", help="Make RESET active high."
    )

    parser.add_argument(
        "-B", "--boot0-active-low", action="store_true", help="Make BOOT0 active low."
    )

    parser.add_argument(
        "-n", "--no-progress", action="store_true", help="Don't show progress bar."
    )

    parser.add_argument(
        "-P",
        "--parity",
        action="store",
        type=str,
        default="even",
        choices=["even", "none"],
        help='Parity: "even" for STM32, "none" for BlueNRG.',
    )

    parser.add_argument("--version", action="version", version=__version__)

    # Hack: We want certain arguments to be required when one
    # of -rwv is specified, but argparse doesn't support
    # conditional dependencies like that. Instead, we add the
    # requirements post-facto and re-run the parse to get the error
    # messages we want. A better solution would be to use
    # subcommands instead of options for -rwv, but this would
    # change the command-line interface.
    #
    # We also use this gross hack to provide a hint about the
    # STM32LOADER_SERIAL_PORT environment variable when -p
    # is omitted; we only set --port as required after the first
    # parse so we can hook in a custom error message.

    configuration = parser.parse_args(arguments)

    if not configuration.port:
        port_arg.required = True
        atexit.register(
            lambda: print(
                "{}: note: you can also set the environment "
                "variable STM32LOADER_SERIAL_PORT".format(parser.prog),
                file=sys.stderr,
            )
        )

    if configuration.read or configuration.write or configuration.verify:
        data_file_arg.nargs = None
        data_file_arg.required = True

    if configuration.read:
        length_arg.required = True
        address_arg.required = True

    parser.parse_args(arguments)

    return configuration
