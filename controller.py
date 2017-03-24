from steamcontroller import SteamController
from struct import pack


def normalize(sc, sci):
    # Detangle touchpad and stick
    lpad_x, lpad_y, joy_x, joy_y = separate_left(sc, sci)
    trans_x = sci.rpad_x
    trans_y = sci.rpad_y
    trans_z = lpad_y
    rot_x = joy_y
    rot_y = 0
    rot_z = lpad_x
    buttons = normalize_buttons(sc, sci)
    print(pack(
        '>' + 'h' * 7,
        trans_x, trans_y, trans_z,
        rot_x, rot_y, rot_z, buttons
    ))
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


SteamController(callback=normalize).run()

# for x in range(-8, 8):
#     print(x, bin(tc(x, 3)))
