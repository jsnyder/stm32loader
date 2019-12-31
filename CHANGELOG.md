
v0.5.1
======
* #25 Fix bug: Mass memory erase by byq77.
* #28 Add support for STM32L4 by rdaforno.
* #29 Add support for more STM32F0 ids by stawiski .
* #30 Add support for STM32F3 by float32.
* #32 Add support for STM32G0x1 by AlexKlimaj.
* #33 More robust bootloader activation by hiviah.
* #35 Support Python 3.8
* #20 Add a 'read flash' example to README
* #34 Add --version argument


v0.5.0
======
* #17 Add support for STM32F03xx4/6 by omerk.
* Drop support for Python 3.2 and 3.3.


v0.4.0
======
* #8: Add support for STM32F7 mcus. By sam-bristow.
* #9: Support data writes smaller than 256 bytes. By NINI1988.
* #10: Make stm32loader useful as a library.
* #4: Bring back support for progress bar.
* #12: Allow to supply the serial port as an environment variable.
* #11: Support paged erase in extended (two-byte addressing) erase mode.
       Note: this is not yet tested on hardware.
* Start using code linting and unit tests.
* Start using Continuous Integration (Travis CI).


v0.3.3
======
* Bugfix: write data, not [data]. By Atokulus.


v0.3.2
======
* Publish on Python Package Index.
* Make stm32loader executable as a module.
* Expose stm32loader as a console script (stm32loader.exe on Windows).


v0.3.1
======
* Make stm32loader installable and importable as a package.
* Make write_memory faster (by Atokulus, see #1).


v0.3.0
=======
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


2018-05
=======
* Make RTS/DTR (boot0/reset) configurable (polarity, swap).


2018-04
=======
* Restore Python 2 compatibility.


2018-03
=======
* Add support for Python 3.
* Remove Psyco and progressbar support.
* Fix checksum calculation bug for paged erase.


2014-04
=======
* Add `-g <address>` (GO command).
* Add known chip IDs.
* Implement extended erase for STM32 F2/F4.


2013-10
=======
* Add Windows compatibility.


2009-04
=======
* Add GPL license.
