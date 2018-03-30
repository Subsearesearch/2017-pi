# TODO: [x] Try 192.168.1.61:8000 first. If that doesn't work, then use
#           67.182.23.160
# TODO: [x] Toggle LED (button byte = 2) on face button push.
# TODO: [x] LIFO queue for faster polling...?
# TODO: [x] Set static IP for RPi.
# TODO: [x] Add exponential sensitivity curve.

import binascii
from struct import pack
from collections import deque
from threading import Thread
from time import sleep
import sys

from requests import get
from requests.exceptions import ConnectionError, ConnectTimeout
from steamcontroller import SCButtons as Masks
from steamcontroller import SteamController

URL = 'http://192.168.1.61:80'

IMU = 0
MULTIPLIER = [1, 0.5]  # Multiply all axes by this
EXPONENT = [1, 3]
LATEST_DATA = deque(maxlen=2)  # Extra length just in case


def send():
    """Continually process controller input and send to the microcontroller."""
    global URL
    global LATEST_DATA
    global MULTIPLIER
    global EXPONENT

    while True:
        try:
            p = LATEST_DATA.pop()
        except IndexError:
            #raise IndexError("The Steam Controller wasn't properly ejected when the last execution failed. Try unplugging it and plugging it back in.")
            pass # p stays the same from previous loop
        print('**{} {}x {}'.format(EXPONENT[0], MULTIPLIER[0], p))
        # r = get(URL, params={'ROV': binascii.hexlify(p)}, timeout=2)
        r = get(URL, params=p, timeout=2)
        print(r.url)
        print('Response text:', r.text)

        # Delay for 50ms
        # sleep(0.05)


def normalize(sc, sci):
    """Detangle touchpad and stick and return bytepack."""
    global MULTIPLIER
    global EXPONENT
    global LATEST_DATA
    m = 32768  # Maximum touchpad value

    rpad_x, rpad_y = sci.rpad_x, sci.rpad_y
    lpad_x, lpad_y, joy_x, joy_y = separate_left(sc, sci)
    # print(rpad_x, rpad_y, lpad_y, 0, joy_x, lpad_x)

    trans_y = int((rpad_y / m) ** EXPONENT[0] * m * MULTIPLIER[0])
    trans_x = int((rpad_x / m) ** EXPONENT[0] * m * MULTIPLIER[0])
    trans_z = int((lpad_y / m) ** EXPONENT[0] * m * MULTIPLIER[0])
    rot_x = int((joy_y / m) ** EXPONENT[0] * m * MULTIPLIER[0])
    rot_y = int((joy_x / m) ** EXPONENT[0] * m * MULTIPLIER[0])
    rot_z = int((lpad_x / m) ** EXPONENT[0] * m * MULTIPLIER[0])
    buttons = normalize_buttons(sc, sci)

    if sci.buttons & (1 << 20):
        exit()

    jsonpack = {
        'xLin': trans_x,
        'yLin': trans_y,
        'zLin': trans_z,
        'xRot': rot_x,
        'yRot': rot_y,
        'zRot': rot_z,
        # 'btns': buttons
        # 'btns': False
    }
    # print(trans_x, trans_y, trans_z, rot_x, rot_y, rot_z)
    bytepack = pack('>7h', trans_x, trans_y, trans_z, rot_x, rot_y, rot_z,
                    buttons)
    # print(bytepack)
    # LATEST_DATA.append(bytepack)
    LATEST_DATA.append(jsonpack)


def normalize_buttons(sc, sci):
    """Return button word."""
    global IMU
    global MULTIPLIER
    global EXPONENT

    # Any button can be pressed to start ROV.
    start = 1 if sci.buttons & 1744830463 else 0

    # Press button 'A' to turn LED on, and press button 'B' to turn LED off.
    led = 6 if sci.buttons & Masks.A else (4 if sci.buttons & Masks.B else 0)

    # Press button 'Y' to turn IMU on, and press button 'X' to turn IMU off.
    # IMU will be disabled by default in ARM code.
    IMU = 8 if sci.buttons & Masks.Y else (0 if sci.buttons & Masks.X else IMU)

    # Left bumper cycles through multipliers
    if not normalize_buttons.lb and sci.buttons & Masks.LB:  # Rising edge
        MULTIPLIER = MULTIPLIER[1:] + [MULTIPLIER[0]]
    normalize_buttons.lb = bool(sci.buttons & Masks.LB)

    # Right bumper cycles through exponents
    if not normalize_buttons.rb and sci.buttons & Masks.RB:
        EXPONENT = EXPONENT[1:] + [EXPONENT[0]]
    normalize_buttons.rb = bool(sci.buttons & Masks.RB)

    return start + led + IMU


normalize_buttons.lb = False
normalize_buttons.rb = False


def separate_left(sc, sci):
    """Detangle the left touchpad and joystick values and return both."""
    if sci.buttons & 1 << 31:
        # Print either pad or joystick, depending on 27th bit
        if sci.buttons & Masks.LPADTOUCH:  # Pad
            pad_x, pad_y = sci.lpad_x, sci.lpad_y
            joy_x, joy_y = separate_left.prev
        else:  # Joystick
            pad_x, pad_y = separate_left.prev
            joy_x, joy_y = sci.lpad_x, sci.lpad_y
        separate_left.prev = (sci.lpad_x, sci.lpad_y)
    else:  # Both aren't pressed, uncomplicated
        # Print both
        if sci.buttons & Masks.LPADTOUCH:
            pad_x, pad_y = sci.lpad_x, sci.lpad_y
            joy_x, joy_y = (0, 0)
        else:
            pad_x, pad_y = (0, 0)
            joy_x, joy_y = sci.lpad_x, sci.lpad_y
    return (pad_x, pad_y, joy_x, joy_y)


separate_left.prev = (0, 0)

# try:
#     get(URL)
# except ConnectionError:
#     URL = 'http://98.255.144.14:8000'

try:
    print('Starting input thread...')
    input_thread = Thread(target=SteamController(callback=normalize).run)
    input_thread.start()
    print('Done')

    print('Starting output thread...')
    output_thread = Thread(target=send)
    output_thread.start()
    print('Done')
    while True:
        sleep(100)
except KeyboardInterrupt:
    print('Wow! Congratulations on breaking everything. Way to go.\nExiting now')
    raise KeyboardInterrupt
    # sys.exit()
