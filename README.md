# Robot Raconteur SpaceMouse Driver for Linux

Robot Raconteur driver for the 3DConnexion SpaceMouse devices using the Linux evdev interface

## Setup

By default the space mouse device is assigned to the group `input`, which requires running the driver as root. To allow running the driver as a normal user, assign the device to the `plugdev` group by creating the file `/etc/udev/rules.d/99-spacemouse.rules` as root with the following contents:

    KERNEL=="event*", ATTRS{idVendor}=="046d", ATTRS{idProduct}=="c62b", MODE="0660", GROUP="plugdev"
    KERNEL=="event*", ATTRS{idVendor}=="256f", ATTRS{idProduct}=="c635", MODE="0660", GROUP="plugdev"
    KERNEL=="event*", ATTRS{idVendor}=="256f", ATTRS{idProduct}=="c633", MODE="0660", GROUP="plugdev"


Run the following to reload the rules:

    sudo udevadm control --reload-rules && sudo udevadm trigger

The `spacenavd` package must be removed or disabled if it is currently installed. Run the following to uninstall:

    sudo apt remove spacenavd

Install python3-robotraconteur

    sudo add-apt-repository ppa:robotraconteur/ppa
    sudo apt-get update
    sudo apt-get install python3-robotraconteur

Install Python dependencies:

    sudo apt install python3-pip python3-evdev python3-yaml python3-setuptools
    pip3 install --user robotraconteurcompanion

## Usage

Start the driver using default configuration:

    python3 robotraconteur_spacemouse_evdev_driver.py --spacemouse-info-file=config/spacemouse_default_joystick_info.yml

By default, this will look for the SpaceMouse Pro. Use the following for the SpaceMouse Compact:

    python3 robotraconteur_spacemouse_evdev_driver.py --spacemouse-info-file=config/spacemouse_default_joystick_info.yml --device=/dev/input/by-id/usb-3Dconnexion_SpaceMouse_Compact-event-if00

If your device isn't listed, look in /dev/input/by-id for the correct device, and pass the full path to `--device=`.

## Example Client

Example client to access the spacemouse:

```
from RobotRaconteur.Client import *
import time

c = RRN.ConnectService("rr+tcp://localhost:59998?service=spacemouse")
    
s = c.joystick_state.Connect()
s.WaitInValueValid()

while True:

    # Read the axes and buttons
    print(s.InValue.axes)
    print(s.InValue.buttons)

    # Delay until the next cycle
    time.sleep(0.1)
```
