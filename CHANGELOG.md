
# Changelog
What changed in which version.


## [0.7.0] - 2023-10-12

### Added
* Support ST BlueNRG-1 and BlueNRG-2 devices.
* Support ST STM32H7 series devices.
* Allow to erase specific pages of flash memory.
* Add command-line switch to protect flash against readout.
* Support Intel hex file format.
* Adopt `flit` as build system.
* Adopt `bump-my-version` as version bumper.


### Cleaned
* Move argument-parsing code to separate file.
* Use long-form argument names in help text and error messages.
* Use IntEnum for commands and responses.



## [0.6.0] - 2023-10-09

### Added
* `#59` Continuous Integration: start running tests and linters on GitHub Actions.
* `#42` `#43` Find flash size for non-standard MCUs (F4, L0).
* Support STM32H7 series.
* Packaging: auto-generate the help output using `cog`.
* Support STM32WL.
* Support Python 3.9 - 3.11.

### Changed
* `#46` `#48` Flush the UART read buffer after MCU reset.
* Use argparse instead of optparse.
* Drop support for Python 2, 3.4 - 3.8.

### Fixed
* `#44` Support flash page size higher than 255.
* `#64` Properly parse address and length given as hexadecimal value.
* `#62` Properly pass device family argument.

### Documented
* `#13` Describe how to extend Stm32Loader.
* `#52` Describe alternative ways to execute the module.
* `#58` Add a list of similar tools.


## [0.5.1] - 2019-12-31
* `#25` Fix bug: Mass memory erase by byq77.
* `#28` Add support for STM32L4 by rdaforno.
* `#29` Add support for more STM32F0 ids by stawiski .
* `#30` Add support for STM32F3 by float32.
* `#32` Add support for STM32G0x1 by AlexKlimaj.
* `#33` More robust bootloader activation by hiviah.
* `#35` Support Python 3.8
* `#20` Add a 'read flash' example to README
* `#34` Add --version argument


## [0.5.0] - 2019-05-02
* `#17` Add support for STM32F03xx4/6 by omerk.
* Drop support for Python 3.2 and 3.3.


## [0.4.0] - 2019-04-19
* `#8`: Add support for STM32F7 mcus. By sam-bristow.
* `#9`: Support data writes smaller than 256 bytes. By NINI1988.
* `#10`: Make stm32loader useful as a library.
* `#4`: Bring back support for progress bar.
* `#12`: Allow to supply the serial port as an environment variable.
* `#11`: Support paged erase in extended (two-byte addressing) erase mode.
       Note: this is not yet tested on hardware.
* Start using code linting and unit tests.
* Start using Continuous Integration (Travis CI).


## [0.3.3] - 2018-08-08
* Bugfix: write data, not [data]. By Atokulus.


## [0.3.2] - 2018-07-31
* Publish on Python Package Index.
* Make stm32loader executable as a module.
* Expose stm32loader as a console script (stm32loader.exe on Windows).


## [0.3.1] -- 2018-07-31
* Make stm32loader installable and importable as a package.
* Make write_memory faster (by Atokulus, see `#1`).


## [0.3.0] - 2018-04-27
* Add version number.
* Add this changelog.
* Improve documentation.
* Support ST BlueNRG devices (configurable parity).
* Add Wiznet W7500 / SweetPeas bootloader chip ID.
* Fix ack-related bugs in (un)protect methods.
* Add 'unprotect' command-line option.
* Read device UID.
* Read device flash size.
* Refactor __main__ functionality into methods.


## 2018-05
* Make RTS/DTR (boot0/reset) configurable (polarity, swap).


## 2018-04
* Restore Python 2 compatibility.


## 2018-03
* Add support for Python 3.
* Remove Psyco and progressbar support.
* Fix checksum calculation bug for paged erase.


## 2014-04
* Add `-g <address>` (GO command).
* Add known chip IDs.
* Implement extended erase for STM32 F2/F4.


## 2013-10
* Add Windows compatibility.


## 2009-04
* Add GPL license.
