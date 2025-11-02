import uart_util
import utime
import micropython
import network
import gc
import json
import sys
import re
import _thread

TIME_UNIT = 60 / (22 * 50)

DOT_DURATION = TIME_UNIT
DASH_DURATION = 3 * TIME_UNIT
ELEMENT_PAUSE = TIME_UNIT
CHAR_PAUSE = 3 * TIME_UNIT

def process_command(json_str):
    try:
        cmd = json.loads(json_str)
        command = cmd.get("command")
        params = cmd.get("params", {})
        
        if command == "get_info":
            return {
                "status": "success",
                "message": {
                    "free_memory": gc.mem_free(),
                    "uptime": utime.ticks_ms()
                }
            }
        
        if command == "get_pwr_on":
            return {
                "status": "success",
                "message": uart_util.is_pwr_on()
            }
        
        if command == "open_pwr":
            uart_util.open_pwr()
            return {
                "status": "success",
                "message": ""
            }
        
        if command == "close_pwr":
            uart_util.close_pwr()
            return {
                "status": "success",
                "message": ""
            }
        
        if command == "blink":
            spd = params["speed"]
            is_start = params["start"]
            if not is_start:
                uart_util.make_it_stop_blink()
                return {
                    "status": "success",
                    "message": ""
                    }
            
            _thread.start_new_thread(uart_util.make_it_blink, (float(spd),))
            return {
                "status": "success",
                "message": ""
            }
        
        if command == "set_volume":
            vol = int(params["vol"])
            return {
                "status": "success",
                "message": uart_util.set_volume(vol)
            }
        
        if command == "set_freq":
            freq = int(params["freq"])
            return {
                "status": "success",
                "message": uart_util.set_freq(freq)
            }
        
        if command == "set_backlight":
            bgl = int(params["bgl"])
            return {
                "status": "success",
                "message": uart_util.set_backlight(bgl)
            }
        
        if command == "set_campus":
            camp = int(params["camp"])
            return {
                "status": "success",
                "message": uart_util.set_campus(camp)
            }
        
        if command == "get_current":
            return {
                "status": "success",
                "message": uart_util.get_current()
            }
        
        if command == "reset":
            return {
                "status": "success",
                "message": uart_util.reset()
            }
        
        if command == "write_text":
            cont = params["content"]
            uart_util.display_word(cont)
            return {
                "status": "success",
                "message": ""
            }
        
        else:
            return {"status": "error", "message": "Unknown command"}
            
    except Exception as e:
        return {"status": "error", "message": str(e).replace("\r\n", "") + ", got original " + json_str}
        
    
def run_uart():
    uart_util.display_word("?DEBUG MODE?")
    if uart_util.is_debug():
        return
    utime.sleep(3)
    uart_util.display_word()
    micropython.kbd_intr(-1)
    while True:
        text = sys.stdin.readline()
        pattern = r'=+(.*?)=+'
        match = re.search(pattern, text)
        if not match: continue
        text = match.group(1).strip()
        response = process_command(text.strip())
        sys.stdout.buffer.write(json.dumps(response) + '\n')
    
def main():
    uart_util.init_uart()
    run_uart()

# purple g blue 5v
#print(uart_util.get_until("AT+RET", "Thank you for using!\r\n"))
#utime.sleep(5)
#print(uart_util.get_until("AT+RET", "Thank you for using!\r\n"))
#utime.sleep(5)
#print(uart_util.get_until("AT+RET", "Thank you for using!\r\n"))
    
#_thread.start_new_thread(uart_util.make_it_blink, ())
#utime.sleep(5)
#uart_util.make_it_stop_blink()
#utime.sleep(5)
    
#print(uart_util.get_current())
#utime.sleep(1)
#print(uart_util.set_freq(880))

if __name__ == '__main__':
    main()
    # make_it_blink(0.45)
    #uart_util.open_pwr()
    


