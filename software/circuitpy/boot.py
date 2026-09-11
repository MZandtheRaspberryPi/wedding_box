import board
import digitalio
import storage

switch = digitalio.DigitalInOut(board.GP16)
switch.direction = digitalio.Direction.INPUT
switch.pull = digitalio.Pull.UP

# If the switch pin is not connected to ground CircuitPython can write to the drive
storage.remount("/", readonly=not switch.value)# Write your code here :-)
