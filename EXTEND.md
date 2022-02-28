
# Extending stm32loader

You can create your own extensions on top of stm32loader's classes.


## Example: Use Raspberry Pi GPIO pins to toggle `BOOT0` and `RESET`

Subclass the `SerialConnection` and override `enable_reset` and `enable_boot0`.

```python3

from RPi import GPIO
from stm32loader.uart import SerialConnection


class RaspberrySerialWithGpio(SerialConnection):
    # Configure which GPIO pins are connected to the STM32's BOOT0 and RESET pins.
    BOOT0_PIN = 2
    RESET_PIN = 3
    
    def __init__(self, serial_port, baud_rate, parity):
        super().__init__(serial_port, baude_rate, parity)
        
        GPIO.setup(self.BOOT0_PIN, GPIO.OUT, initial=GPIO.LOW)
        GPIO.setup(self.RESET_PIN, GPIO.OUT, initial=GPIO.HIGH)
        
    def enable_reset(self, enable=True):
        """Enable or disable the reset IO line."""
        # Reset is active low.
        # To enter reset, write a 0.
        level = 1 - int(enable)
        
        GPIO.output(self.RESET_PIN, level)

    def enable_boot0(self, enable=True):
        """Enable or disable the boot0 IO line."""
        level = int(enable)
        
        GPIO.output(self.BOOT0_PIN, level)
```

Connect to the UART and instantiate a Bootloader object.

```python3

from stm32loader.bootloader import Stm32Bootloader

from raspberrystm32 import RaspberrySerialWithGpio


connection = RaspberrySerialWithGpio("/dev/cu.usbserial-A5XK3RJT")
connection.connect()
stm32 = Stm32Bootloader(connection, device_family="F1")
```

Now you can use all of the Stm32Bootloader methods.

```python3
stm32.reset_from_system_memory()
print(stm32.get_version())
print(stm32.get_id())
print(stm32.get_flash_size())
```
