
# Running stm32loader


## Execute as a module

After installing stm32loader with `pip`, it's available as a Python module.

You can execute this with `python -m [modulename]`.

```shell
python3 -m stm32loader
```


## Execute as a module without installing

You can also run `stm32loader` without installing it.  You do need `pyserial` though.

Make sure you are in the root of the repository, or the repository is in `PYTHONPATH`.

```shell
python3 -m pip install pyserial --user
python3 -m stm32loader
```


## Execute main.py directly

The file `main.py` also runs the `stm32loader` program when executed.
Make sure the module can be found; add the folder of the repository to `PYTHONPATH`.

```shell
PYTHONPATH=. python3 stm32loader/main.py
```


## Use from Python

You can use the classes of `stm32loader` from a Python script.

Example:

```python
from stm32loader.main import Stm32Loader

loader = Stm32Loader()
loader.configuration.port = "/dev/cu.usbserial-A5XK3RJT"
loader.connect()
loader.stm32.readout_unprotect()
loader.disconnect()
```
