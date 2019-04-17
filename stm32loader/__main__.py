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
Execute stm32loader as a module.

This does exactly the same as manually calling 'python stm32loader.py'.
"""

from .stm32loader import main as stm32loader_main


def main():
    """
    Separate main method, different from stm32loader.main.

    This way it it can be used as an entry point for a console script.
    :return None:
    """
    stm32loader_main()


if __name__ == "__main__":
    main()
