
vnext
=====
* Add support for STM32F7 mcus. By sam-bristow.

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
