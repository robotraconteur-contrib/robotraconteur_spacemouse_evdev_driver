
import RobotRaconteur as RR
RRN = RR.RobotRaconteurNode.s
import RobotRaconteurCompanion as RRC
import argparse
import sys
import threading
import numpy as np
import traceback
from RobotRaconteurCompanion.Util.InfoFileLoader import InfoFileLoader
from RobotRaconteurCompanion.Util.DateTimeUtil import DateTimeUtil
from RobotRaconteurCompanion.Util.SensorDataUtil import SensorDataUtil
from RobotRaconteurCompanion.Util.AttributesUtil import AttributesUtil

from evdev import InputDevice, ecodes

DEFAULT_DEVICE="/dev/input/by-id/usb-3Dconnexion_SpaceMouse_Pro-event-mouse"
AXIS_MAX=350

class SpacemouseImpl:
    
    def __init__(self, evdev_device, spacemouse_info):

        self._dev = evdev_device
        self.device_info = spacemouse_info.device_info
        self.joystick_info = spacemouse_info

        self._lock = threading.Lock()

        self._joystick_state = RRN.GetStructureType('com.robotraconteur.hid.joystick.JoystickState')
        self._joystick_state_sensor_data = RRN.GetStructureType('com.robotraconteur.hid.joystick.JoystickStateSensorData')

        self._date_time_util = DateTimeUtil(RRN)
        self._sensor_data_util = SensorDataUtil(RRN)

        self._axes_state = np.zeros((6,),dtype=np.int16)
        self._buttons_state = np.zeros((4,),dtype=np.uint8)

        self._timer = RRN.CreateTimer(0.02, self._timer_cb)
        self._timer.Start()
        self._seqno = 0

    def RRServiceObjectInit(self, ctx, service_path):
        self._downsampler = RR.BroadcastDownsampler(ctx)
        self._downsampler.AddWireBroadcaster(self.joystick_state)
        self._downsampler.AddPipeBroadcaster(self.joystick_sensor_data)
        self._downsampler.AddWireBroadcaster(self.device_clock_now)

    def _update_state(self):
        # Update the state. Limit to 1000 updates per cycle

        i = 0
        while True:
            i += 1
            if i > 1000:
                break
            try:
                event = self._dev.read_one()
                if event is None:
                    break
                if event.type == ecodes.EV_REL:
                    if event.code >= 0 and event.code < 6:
                        self._axes_state[event.code] = (event.value * 32767) / AXIS_MAX
                if event.type == ecodes.EV_KEY:
                    if event.code >= 268 and event.code < 273:
                        if event.value == 0:
                            self._buttons_state[event.code-268]=0
                        else:
                            self._buttons_state[event.code-268]=1
            except:
                traceback.print_exc()
                self._axes_state = np.zeros((6,),dtype=np.int16)
                self._buttons_state = np.zeros((4,),dtype=np.uint8)
                break

    def _timer_cb(self, timer_evt):
        with self._lock:
            self._seqno+=1
            self._update_state()

            joy_state = self._joystick_state()
            joy_state.axes = self._axes_state
            joy_state.buttons = self._buttons_state
            joy_state.hats = np.zeros((0,),dtype=np.uint8)

            joy_sensor_data = self._joystick_state_sensor_data()
            joy_sensor_data.data_header = self._sensor_data_util.FillSensorDataHeader(self.device_info,self._seqno)
            joy_sensor_data.joystick_state = joy_state

            self.joystick_state.OutValue = joy_state
            self.joystick_sensor_data.AsyncSendPacket(joy_sensor_data, lambda: None)

    @property
    def isoch_downsample(self):
        return self._downsampler.GetClientDownsample(RR.ServerEndpoint.GetCurrentEndpoint())

    @isoch_downsample.setter
    def isoch_downsample(self, value):
        return self._downsampler.SetClientDownsample(RR.ServerEndpoint.GetCurrentEndpoint(),value)

    @property
    def isoch_info(self):
        ret = self._isoch_info()
        ret.update_rate = self._fps
        ret.max_downsample = 100
        ret.isoch_epoch = np.zeros((1,),dtype=self._date_time_utc_type)
        

def main():
    parser = argparse.ArgumentParser(description="Evdev based driver for 3DConnexion SpaceMouse")
    parser.add_argument("--spacemouse-info-file", type=argparse.FileType('r'),default=None,required=True,help="SpaceMouse info file (required)")
    parser.add_argument("--device", type=str, default=DEFAULT_DEVICE, help="the spacemouse device to open (default /dev/input/by-id/usb-3Dconnexion_SpaceMouse_Pro-event-mouse)")
    parser.add_argument("--wait-signal",action='store_const',const=True,default=False, help="wait for SIGTERM orSIGINT (Linux only)")

    args, _ = parser.parse_known_args()

    spacemouse_dev = InputDevice(args.device)
    spacemouse_dev.grab()

    RRC.RegisterStdRobDefServiceTypes(RRN)

    with args.spacemouse_info_file:
        spacemouse_info_text = args.spacemouse_info_file.read()

    info_loader = InfoFileLoader(RRN)
    spacemouse_info, spacemouse_ident_fd = info_loader.LoadInfoFileFromString(spacemouse_info_text, "com.robotraconteur.hid.joystick.JoystickInfo", "device")

    attributes_util = AttributesUtil(RRN)
    spacemouse_attributes = attributes_util.GetDefaultServiceAttributesFromDeviceInfo(spacemouse_info.device_info)

    spacemouse = SpacemouseImpl(spacemouse_dev, spacemouse_info)
    
    with RR.ServerNodeSetup("com.robotraconteur.hid.joystick.spacemouse",59998):

        service_ctx = RRN.RegisterService("spacemouse","com.robotraconteur.hid.joystick.Joystick",spacemouse)
        service_ctx.SetServiceAttributes(spacemouse_attributes)

        if args.wait_signal:  
            #Wait for shutdown signal if running in service mode          
            print("Press Ctrl-C to quit...")
            import signal
            signal.sigwait([signal.SIGTERM,signal.SIGINT])
        else:
            #Wait for the user to shutdown the service
            if (sys.version_info > (3, 0)):
                input("Server started, press enter to quit...")
            else:
                raw_input("Server started, press enter to quit...")


if __name__ == "__main__":
    main()
