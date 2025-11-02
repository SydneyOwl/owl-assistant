import json
import os
import serial
import time
from threading import Lock

COM ="/dev/ttyUSB0"

mutex = Lock()

ser: serial.Serial = None

def setPrt(port):
    global COM
    COM = port

def create():
    global ser
    try:
        with mutex:
            if ser is not None: ser.close()
            if not os.path.exists(COM): return False
            ser = serial.Serial(COM, 115200, timeout=0.5)
            return True
    except Exception as e:
        print(repr(e))
        return False

def testPort():
    try:
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        return True
    except Exception:
        ser = None
        return False

def isOpen():
    if ser is not None and testPort(): return True
    return create()


def write_common(inst: bytes):
    with mutex:
        try:
            ser.readlines()
            ser.write(inst)
            time.sleep(0.1)
            res = ser.readline()
            print(res)
            return res
        except Exception as k:
            print(repr(k))
            create()
            return "ERR"
        finally:
            ser.readlines()


def setter(typer, val = {}):
    print('=={"command":"' + typer +'","params":' + str(val) + '}===\r\n')
    resp = write_common(('==={"command":"' + typer +'","params":' + json.dumps(val) + '}===\r\n').encode())
    return json.loads(resp)


def set_volume(vol: int):
    vol = int(vol)
    return setter("set_volume", {"vol" : vol})["message"]


def set_freq(freq: int):
    freq = int(freq)
    return setter("set_freq",  {"freq" : freq})["message"]


def set_backlight(timeout: int):
    return True
    # timeout = int(timeout)
    # if timeout < 10:
    #     return setter("BANK", "0" + str(timeout))
    # return setter("BANK", timeout)


def set_campus(on: int):
    return setter("set_campus", {"camp" : on})["message"]


def get_current():
    return setter("get_current")

def get_pwr_on():
    return setter("get_pwr_on")["message"]

def reset():
    return setter("reset")["message"]

def open_power():
    return setter("open_pwr")["message"]

def close_power():
    return setter("close_pwr")["message"]

def blink(speed, start):
    return setter("blink", {
        "speed": speed,
        "start": start
    })["message"]

def write_text(ctt):
    return setter("write_text", {"content": ctt})["message"]

def close():
    ser.close()


if __name__ == "__main__":
    create()
    print(setter("get_info"))
    close()
