import argparse
import numpy as np
import hid
from time import sleep

import requests


def get_biggest_diff_index(array1, array2) -> int:
    array1 = np.array(array1)
    array2 = np.array(array2)
    diff = abs(array1 - array2)
    print(diff)
    index = np.unravel_index(diff.argmax(), diff.shape)
    return int(index[0])


controller_calibration = {
    "speed": 2,
    "steer": 3,
    "switch_manual": (6, 1),    # Byte 6, Bit 1
    "switch_auto": (6, 0),      # Byte 6, Bit 0
    "stop": (5, 5),             # Byte 5, Bit 5
    "drive": (5, 7),            # Byte 5, Bit 7
}
def calib_gamepad(controller):
    print("Starting gamepad calibration")

    while True:
        print(controller.read(64))
        sleep(0.2)


old_button_states = {
    "speed": 0,
    "steer": 0,
    "switch_manual": 0,
    "switch_auto": 0,
    "stop": 0,
    "drive": 0,
}

def get_bit_at_position(byte, position):
    return (byte >> position) & 1

def is_button_press_changed(raw_data, button_name):
    byte = raw_data[controller_calibration[button_name][0]]
    new_press_status = get_bit_at_position(byte, controller_calibration[button_name][1])
    try:
        if new_press_status > old_button_states[button_name]:
            return True
        return False

    finally:
        old_button_states[button_name] = new_press_status


def main():
    parser = argparse.ArgumentParser(description='Control the car with a gamepad')
    parser.add_argument('hid_device', type=str)
    parser.add_argument('--drive_server_ip', default="192.168.0.135", type=str, required=False)
    parser.add_argument('--drive_server_port', default=5000, type=int, required=False)
    parser.add_argument('--default_drive_speed', default=0.3, type=float, required=False)
    parser.add_argument('--max_drive_speed', default=0.6, type=float, required=False)
    parser.add_argument('--max_steer', default=1, type=float, required=False)
    args = parser.parse_args()

    # Setup gamepad
    gamepad = hid.device()
    gamepad.open(*([int(a, 16) for a in args.hid_device.split(":")]))
    gamepad.set_nonblocking(True)
    # calib_gamepad(gamepad)

    # Run controls
    print("Starting controls")
    while True:
        raw_data = gamepad.read(64)
        if not raw_data:
            continue

        speed_norm = raw_data[controller_calibration["speed"]] / 128. - 1
        speed_norm = -speed_norm
        speed_norm *= args.max_drive_speed
        if speed_norm != old_button_states["speed"]:
            old_button_states["speed"] = speed_norm
            print("Speed:", speed_norm)
            requests.post(f"http://{args.drive_server_ip}:{args.drive_server_port}/set_speed", json={"speed": speed_norm})

        steer_norm = raw_data[controller_calibration["steer"]] / 128. - 1
        steer_norm *= args.max_steer
        if steer_norm != old_button_states["steer"]:
            old_button_states["steer"] = steer_norm
            print("Steer:", steer_norm)
            requests.post(f"http://{args.drive_server_ip}:{args.drive_server_port}/set_steer", json={"steer": steer_norm})

        if is_button_press_changed(raw_data, "switch_manual"):
            print("Switch manual")
            requests.post(f"http://{args.drive_server_ip}:{args.drive_server_port}/set_speed", json={"speed": 0})
            requests.post(f"http://{args.drive_server_ip}:{args.drive_server_port}/set_auto_steer", json={"auto_steer": False})
            requests.post(f"http://{args.drive_server_ip}:{args.drive_server_port}/set_steer", json={"steer": 0})

        if is_button_press_changed(raw_data, "switch_auto"):
            print("Switch auto")
            requests.post(f"http://{args.drive_server_ip}:{args.drive_server_port}/set_auto_steer", json={"auto_steer": True})

        if is_button_press_changed(raw_data, "stop"):
            print("Stop")
            requests.post(f"http://{args.drive_server_ip}:{args.drive_server_port}/set_speed", json={"speed": 0})

        if is_button_press_changed(raw_data, "drive"):
            print("Drive")
            requests.post(f"http://{args.drive_server_ip}:{args.drive_server_port}/set_speed", json={"speed": args.default_drive_speed})


if __name__ == '__main__':
    main()
