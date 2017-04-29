# TODO: [x] Try 192.168.1.61:8000 first. If that doesn't work, then use 67.182.23.160
# TODO: [x] Toggle LED (button byte = 2) on face button push.
# TODO: [ ] LIFO queue for faster polling...?
# TODO: [x] Set static IP for RPi.

import binascii
from time import sleep
from struct import pack
from timeit import timeit
from requests.exceptions import ConnectionError, ConnectTimeout, ReadTimeout
from requests import get

from steamcontroller import SCButtons as Masks
from steamcontroller import SteamController

#Joey: Changed port from 8000 to 80
URL = 'http://192.168.1.61:80'

IMU = 0
MULTIPLIER = [1, 0.5]  # Multiply all axes by this

def send(sc, sci):
    """Process controller input and send to the microcontroller."""
    global URL

    p = normalize(sc, sci)
    r = get(URL, params={'ROV': binascii.hexlify(p)}, timeout=2)
    # print('Response code:', r.status_code)

    # print('Response text:', r.text)
    # print('Request URL:  ', r.url)

    # Delay for 50ms
    sleep(0.05)

#Joey: The parameter LED=Toggle no longer toggles the LED.
def test_network():
    try:
        r = get('http://67.182.23.160:8000', params={'LED': 'Toggle'}, timeout=2)
        print(r.text)
    except ConnectTimeout:
        pass


def normalize(sc, sci):
    """Detangle touchpad and stick and return bytepack."""
    global MULTIPLIER
    lpad_x, lpad_y, joy_x, joy_y = separate_left(sc, sci)
    trans_x = int(MULTIPLIER[0] * sci.rpad_x)
    trans_y = int(MULTIPLIER[0] * sci.rpad_y)
    trans_z = int(MULTIPLIER[0] * lpad_y)
    rot_x = int(MULTIPLIER[0] * 0)
    rot_y = int(MULTIPLIER[0] * joy_x)
    rot_z = int(MULTIPLIER[0] * lpad_x)
    buttons = normalize_buttons(sc, sci)

    #Print button word.
    # print(buttons)
    #Print Steam controller buttons.
    # print(format(sci.buttons, '032b'))

    if sci.buttons & (1<<20):
        exit()

    bytepack = pack('>7h', trans_x, trans_y, trans_z, rot_x, rot_y, rot_z,
                    buttons)
    print(bytepack)
    return bytepack
    # print(len(bin(sci.rpad_y)), bin(sci.rpad_y), sci.rpad_y)


def normalize_buttons(sc, sci):
    """Return button word."""
    global IMU
    global MULTIPLIER

    #Any button can be pressed to start ROV.
    start = 1 if sci.buttons & 1744830463 else 0

    #Press button 'A' to turn LED on, and press button 'B' to turn LED off.
    led = 6 if sci.buttons & Masks.A else (4 if sci.buttons & Masks.B else 0)

    #Press button 'Y' to turn IMU on, and press button 'X' to turn IMU off. IMU will be disabled by default in ARM code.
    IMU = 8 if sci.buttons & Masks.Y else (0 if sci.buttons & Masks.X else IMU)

    # Left bumper cycles through multipliers
    if not normalize_buttons.lb and sci.buttons & Masks.LB:  # Rising edge detector
        print('Cycling MULTIPLIER')
        MULTIPLIER = MULTIPLIER[1:] + [MULTIPLIER[0]]
        print('New multiplier:', MULTIPLIER)
    normalize_buttons.lb = bool(sci.buttons & Masks.LB)

    return start + led + IMU

normalize_buttons.lb = False


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


try:
    get(URL)
except ConnectionError:
    URL = 'http://67.182.23.160:8000'

print('Starting handler...')
SteamController(callback=send).run()
