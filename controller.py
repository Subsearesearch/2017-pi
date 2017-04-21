import socket
from struct import pack

from steamcontroller import SteamController


def send(sc, sci, sock):
    """Process controller input and send over socket sock."""
    p = normalize(sc, sci)
    sock.send(p)


def normalize(sc, sci):
    # Detangle touchpad and stick and return bytepack
    lpad_x, lpad_y, joy_x, joy_y = separate_left(sc, sci)
    trans_x = sci.rpad_x
    trans_y = sci.rpad_y
    trans_z = lpad_y
    rot_x = joy_y
    rot_y = 0
    rot_z = lpad_x
    buttons = normalize_buttons(sc, sci)
    return pack('>' + 'h' * 7, trans_x, trans_y, trans_z, rot_x, rot_y, rot_z,
                buttons)
    # print(len(bin(sci.rpad_y)), bin(sci.rpad_y), sci.rpad_y)


def normalize_buttons(sc, sci):
    return 1 if sci.buttons else 0


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

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect(('192.168.1.61', 80))

SteamController(callback=send, callback_args=s).run()
