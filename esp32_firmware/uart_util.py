import utime
from machine import UART, Pin, I2C
from ssd1306 import SSD1306_I2C

def init_uart():
    global pn_pwr1,pn_pwr2,mode_pin,pn_uart,pn_oled,do_blink
    pn_pwr1 = Pin(25, Pin.OUT)
    pn_pwr1.value(0)

    pn_pwr2 = Pin(27, Pin.OUT)
    pn_pwr2.value(0)

    mode_pin = Pin(13, Pin.IN, Pin.PULL_UP)

    pn_uart = UART(2, 38400, rx=16, tx=17)

    i2c = I2C(sda=Pin(21), scl=Pin(22))

    pn_oled = SSD1306_I2C(128, 64, i2c)

    pn_oled.poweroff()

    do_blink = False
    

def is_debug():
    return mode_pin.value() == 0

def is_pwr_on():
    return pn_pwr1.value() == 1

def open_pwr():  # O: ---
    pn_pwr1.value(1)

def close_pwr():  # C: -.-.
    pn_pwr1.value(0)
    
def display_word(disp_str = None):
    if disp_str is None or disp_str == "":
        pn_oled.poweroff()
        return
    
    pn_oled.poweron()
    pn_oled.fill(0)
    
    lines = wrap_text(disp_str, max_chars=21)
    
    for i, line in enumerate(lines):
        if i < 8:
            pn_oled.text(line, 0, i * 8)
    
    pn_oled.show()

def wrap_text(text, max_chars=21):
    lines = []
    words = text.split(' ')
    current_line = []
    
    for word in words:
        # 检查当前行加上新单词是否超过最大字符数
        test_line = ' '.join(current_line + [word])
        if len(test_line) <= max_chars:
            current_line.append(word)
        else:
            # 如果单个单词就超长，强制分割
            if len(word) > max_chars:
                if current_line:
                    lines.append(' '.join(current_line))
                    current_line = []
                # 分割长单词
                for i in range(0, len(word), max_chars):
                    lines.append(word[i:i+max_chars])
            else:
                # 正常换行
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
    
    # 添加最后一行
    if current_line:
        lines.append(' '.join(current_line))
    
    return lines

def make_it_blink(speed = 0.45, rep_time = 100000):
    global do_blink
    if speed < 0.2: speed = 0.2
    if do_blink: return
    do_blink = True
    while do_blink and rep_time > 0:
        rep_time = rep_time - 1
        pn_pwr2.value(1)
        utime.sleep(speed)
        pn_pwr2.value(0)
        utime.sleep(speed)
    pn_pwr2.value(0)
    
def make_it_stop_blink():
    global do_blink
    do_blink = False

def reinit():
    global pn_uart
    #make_it_blink(0.2, 5)
    if pn_uart:
        try:
            pn_uart.deinit()
        except:
            pass
        
    utime.sleep_ms(50)
    pn_uart = UART(2, 38400, rx=16, tx=17)
    utime.sleep_ms(100)
    
def write_common(inst):
    try:
        while pn_uart.any():
            pn_uart.read(pn_uart.any())
        pn_uart.write(inst)
        utime.sleep_ms(200)
        return pn_uart.readline()
    except Exception as e:
        reinit()
        return b"ERR"
    finally:
        try:
            while pn_uart.any():
                pn_uart.read(pn_uart.any())
        except:
            pass

def write_and_get_until(inst, finish_at):
    try:
        while pn_uart.any():
            pn_uart.read(pn_uart.any())
        pn_uart.write(inst)
        
        timeout = 5000
        start_time = utime.ticks_ms()
        data = b""
        
        while utime.ticks_diff(utime.ticks_ms(), start_time) < timeout:
            if pn_uart.any():
                chunk = pn_uart.read(pn_uart.any())
                data += chunk
                if finish_at.encode() in data:
                    return data
            utime.sleep_ms(10)
        
        raise Exception("Timeout!")
        
    except Exception as e:
        reinit()
        return b"ERR"
    finally:
        try:
            while pn_uart.any():
                pn_uart.read(pn_uart.any())
        except:
            pass
        
def fm_setter(typer, val):
    resp = write_common("AT+{}={}\r\n".format(typer, val).encode())
    if "ERR" not in str(resp):
        return True
    return False


def set_volume(vol: int):
    vol = int(vol)
    if vol < 10:
        return fm_setter("VOL", "0" + str(vol))
    return fm_setter("VOL", vol)


def set_freq(freq: int):
    return fm_setter("FRE", freq)


def set_backlight(timeout: int):
    if timeout < 10:
        return fm_setter("BANK", "0" + str(timeout))
    return fm_setter("BANK", timeout)


def set_campus(on: int):
    return fm_setter("CAMPUS", on)


def get_current():
    res = str(write_and_get_until(b"AT+RET", "Thank you for using!\r\n"))
    if res == "ERR":
        return {}
    fin = res.split("\\r\\n")
    vol = fin[1].split("=")[1]
    fre = fin[2].split("=")[1]
    bak = 0
    if fin[4] == "BANK_OFF":
        bak = 0
    elif fin[4] == "BANK_ON":
        bak = 1
    else:
        bak = fin[4].split("=")[1][:-1]
    camp = fin[5] == "CAMPOS_ON"
    return {"vol": vol, "fre": fre, "bak": bak, "camp": camp}


def reset():
    bk = write_common(b"AT+CR")
    return "OK" in str(bk)

def pauseplay():
    write_common(b"AT+PAUS")
    
if __name__ == '__main__':
    init_uart()
    while True:
        display_word("Debug Mode")
        utime.sleep(2)
        display_word(" ")
        utime.sleep(2)

