# TODO: [x] Try 192.168.1.61:8000 first. If that doesn't work, then use 67.182.23.160
# TODO: [x] Toggle LED (button byte = 2) on face button push.
# TODO: [ ] LIFO queue for faster polling...?
# TODO: [ ] Set static IP for RPi.

import binascii
from struct import pack
from timeit import timeit
from requests.exceptions import ConnectionError, ConnectTimeout, ReadTimeout
from requests import get

from steamcontroller import SteamController


URL = 'http://192.168.1.61:8000'


def send(sc, sci):
    """Process controller input and send to the microcontroller."""
    global URL
    p = normalize(sc, sci)
    # print(binascii.hexlify(p))
    r = get(URL, params={'ROV': binascii.hexlify(p)}, timeout=2)
    print('Response code:', r.status_code)
    # print('Response text:', r.text)
    # print('Request URL:  ', r.url)


def test_network():
    try:
        r = get('http://67.182.23.160:8000', params={'LED': 'Toggle'}, timeout=2)
        print(r.text)
    except ConnectTimeout:
        pass


def normalize(sc, sci):
    """Detangle touchpad and stick and return bytepack."""
    lpad_x, lpad_y, joy_x, joy_y = separate_left(sc, sci)
    trans_x = sci.rpad_x
    trans_y = sci.rpad_y
    trans_z = lpad_y
    rot_x = 0
    rot_y = joy_x
    rot_z = lpad_x
    buttons = normalize_buttons(sc, sci)
    print(buttons)
    return pack('>7h', trans_x, trans_y, trans_z, rot_x, rot_y, rot_z,
                buttons)
    # print(len(bin(sci.rpad_y)), bin(sci.rpad_y), sci.rpad_y)


def normalize_buttons(sc, sci):
    start = 1 if sci.buttons & 1744830463 else 0
    led = 2 if sci.buttons & (0b1111 << 12) else 0
    return start + led


def separate_left(sc, sci):
    if sci.buttons & 1 << 31:
        # Print either pad or joystick, depending on 27th bit
        if sci.buttons & 1 << 27:  # Pad
            pad_x, pad_y = sci.lpad_x, sci.lpad_y
            joy_x, joy_y = separate_left.prev
        else:  # Joystick
            pad_x, pad_y = separate_left.prev
            joy_x, joy_y = sci.lpad_x, sci.lpad_y
        separate_left.prev = (sci.lpad_x, sci.lpad_y)
    else:  # Both aren't pressed, uncomplicated
        # Print both
        if sci.buttons & 1 << 27:
            pad_x, pad_y = sci.lpad_x, sci.lpad_y
            joy_x, joy_y = [0] * 2
        else:
            pad_x, pad_y = (0, 0)
            joy_x, joy_y = sci.lpad_x, sci.lpad_y
    return (pad_x, pad_y, joy_x, joy_y)


separate_left.prev = (0, 0)

# print(timeit('test_network()', setup='from __main__ import test_network', number=50))

try:
    get(URL)
except ConnectionError:
    URL = 'http://67.182.23.160:8000'


print('Starting handler...')
SteamController(callback=send).run()
