import hashlib
import io
import traceback
from PIL import Image
from escpos.printer import Usb as thermalUsb
import queue
import os
import time
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import filetype

task = queue.Queue(-1)
app = Flask(__name__)
CORS(app, resources=r"/*")
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024


class UsbPrinter(thermalUsb):
    def __init__(self, vid, pid, not_printer=False):
        self.not_printer = not_printer
        self.data = ""
        if not_printer:
            return
        super().__init__(vid, pid)

    def imageImproved(self, source):
        RESIZE_WIDTH = 400
        im = Image.open(source)
        width = im.size[0]
        length = im.size[1]
        if width > length:
            im = im.transpose(Image.ROTATE_90)
            factor_resize = RESIZE_WIDTH / length
            im = im.resize((400, int(width * factor_resize)), Image.ANTIALIAS)
        else:
            factor_resize = RESIZE_WIDTH / width
            im = im.resize((400, int(length * factor_resize)), Image.ANTIALIAS)
        self.image(im)

    def printTxt(self, txt):
        if not self.not_printer:
            self._raw("{}\n".format(txt).encode("GB18030"))
        else:
            self.data += txt + "\n"

    def exportData(self):
        self.data = ""
        self.printTxt("Status Report Ticket")
        self.printTxt("Reporter v0.1.0bSydneycat.")
        sen = eval(requests.get(url="http://xxxx/getSensor").text)
        general = eval(str(os.popen("./linux_json_api.sh general_info").readline()))
        load = eval(str(os.popen("./linux_json_api.sh load_avg").readline()))
        temp = str(os.popen("./linux_json_api.sh cpu_temp").readline())  ##)
        neicun = eval(str(os.popen("./linux_json_api.sh current_ram").readline()))
        cpuinfo = eval(str(os.popen("./linux_json_api.sh cpu_info").readline()))
        partitions = eval(
            os.popen("./linux_json_api.sh disk_partitions").readline()
        )  ##)

        self.printTxt("----System info-----")
        self.printTxt("Operation System: {}".format(general["OS"]))
        self.printTxt("Uptime: {}".format(general["Uptime"]))
        self.printTxt(
            "LoadAvg: {}, {}, {}".format(
                load["1_min_avg"], load["5_min_avg"], load["15_min_avg"]
            )
        )
        self.printTxt("")
        self.printTxt("-----CPU info-----")
        self.printTxt("CPUArch: {}".format(cpuinfo["Architecture"]))
        self.printTxt("Core: {}".format(cpuinfo["CPU(s)"]))
        self.printTxt("On-line CPU(s) list: {}".format(cpuinfo["On-line CPU(s) list"]))
        self.printTxt("Model: {}".format(cpuinfo["Model name"]))
        self.printTxt("Temperature: {}".format(temp))
        self.printTxt("")
        self.printTxt("-----RAM Info-----")
        self.printTxt("Total: {}".format(neicun["total"]))
        self.printTxt("Used: {}".format(neicun["used"]))
        self.printTxt("Available: {}".format(neicun["available"]))
        self.printTxt("")
        self.printTxt("-----Disk Info-----")
        for i in partitions:  # range(partitions):
            self.printTxt(
                "{}: {}/{}, used {}, mount@{}".format(
                    i["file_system"], i["used"], i["size"], i["used%"], i["mounted"]
                )
            )
        self.printTxt("")
        self.printTxt("-----Sensor Info-----")
        tem = sen[0]["temp"]
        hum = sen[0]["humi"]
        batt = sen[0]["batt"]
        volt = sen[0]["volt"]
        tie = sen[0]["time"]
        mac = sen[0]["name"]
        rssi = sen[0]["rssi"]
        Auth = False
        self.printTxt("===Sensor Inside===")
        self.printTxt("Temperature: {}℃".format(tem))
        self.printTxt("Humidity: {}%".format(hum))
        self.printTxt("Batt: {}%".format(batt))
        self.printTxt("Volt: {}v".format(volt))
        self.printTxt("Rssi: {}dBm".format(rssi))
        self.printTxt("Mac: {}".format(mac))
        self.printTxt("Report@: {}".format(tie))
        tem = sen[1]["temp"]
        hum = sen[1]["humi"]
        batt = sen[1]["batt"]
        volt = sen[1]["volt"]
        tie = sen[1]["time"]
        mac = sen[1]["name"]
        rssi = sen[1]["rssi"]
        self.printTxt("===Sensor Outside===")
        self.printTxt("Temperature: {}℃".format(tem))
        self.printTxt("Humidity: {}%".format(hum))
        self.printTxt("Batt: {}%".format(batt))
        self.printTxt("Volt: {}v".format(volt))
        self.printTxt("Rssi: {}dBm".format(rssi))
        self.printTxt("Mac: {}".format(mac))
        self.printTxt("Report@: {}".format(tie))
        self.printTxt("<<<<<<<<<<<<<<<<<<<<<")
        self.printTxt("Done.")
        self.printTxt("Sign below: ")
        self.printTxt("")
        self.printTxt("")
        self.printTxt("____________")
        self.printTxt("PrintTime: {}".format(time.asctime(time.localtime())))  # )
        self.printTxt("")
        self.printTxt("")
        self.printTxt("")


@app.before_request
def check_auth_header():
    # hidden
    return None

@app.route("/thermal/sysPrint", methods=["POST"])
def printInfo():
    try:
        cups_conn = UsbPrinter(0x0416, 0x5011)
        cups_conn.exportData()
    except Exception as e:
        print(repr(e))
        return jsonify({"code": 400})
    finally:
        cups_conn.close()
        return jsonify({"code": 200})


@app.route("/thermal/fetchATIS", methods=["POST"])
def printInfoer():
    general = eval(str(os.popen("./linux_json_api.sh general_info").readline()))
    temp = str(os.popen("./linux_json_api.sh cpu_temp").readline())  ##)
    sen = eval(requests.get(url="http://xxxx/getSensor").text)
    return jsonify(
        {
            "code": 200,
            "data": {
                "terminal": {"general": general, "temp": temp},
                # "sensor": {
                #     "sensor1": {"temp": 0, "hum": 0},
                #     "sensor2": {"temp": 0, "hum": 0},
                # },
                "sensor": {
                    "sensor1": {"temp": sen[0]["temp"], "hum": sen[0]["humi"]},
                    "sensor2": {"temp": sen[1]["temp"], "hum": sen[1]["humi"]},
                },
            },
        }
    )

@app.route("/thermal/rawInfo", methods=["POST"])
def getRawInfo():
    dic = request.get_json()
    targetType = dic["req"]
    rawRes = eval(str(os.popen("./linux_json_api.sh " + targetType).readline()))
    return jsonify({
        "code": 200,
        "data": rawRes
    })

@app.route("/thermal/fetchInfo", methods=["POST"])
def printInfo1():
    try:
        cups_conn = UsbPrinter(0x0416, 0x5011, True)
        cups_conn.exportData()
        return jsonify({"code": 200, "data": cups_conn.data})
    except Exception as e:
        traceback.print_exc(e)
        return jsonify({"code": 400})
    finally:
        cups_conn.close()

def isOnline():
    uslb = os.popen("lsusb")
    onXPP = "0416:5011" in uslb.read()
    uslb.close()
    return onXPP

@app.route("/thermal/online", methods=["POST"])
def tOnline():
    if isOnline():
        return {"code": 200}
    return {"code": 201}


@app.route("/thermal/upload", methods=["POST"])
def upload():
    try:
        if not isOnline(): return jsonify({"code": 500, "msg":"设备离线！"})
        cups_conn = UsbPrinter(0x0416, 0x5011)
        if request.method == "POST":
            if "application/json" in request.content_type:
                dic = request.get_json()
            else:
                dic = request.form.to_dict()
            if "application/x-www-form-urlencoded" in request.content_type:
                strs = dic["file"]
                if len(strs) == 0 or len(strs) > 1000:
                    return jsonify({"code": 500, "msg":"长度超过1000字符！"})
                cups_conn.printTxt(strs + "\n\n")
                # if "printComment" not in dic:
                #     cups_conn.printTxt(
                #         "Finish at {}. \n您所上传的内容将会在打印完成后以不可逆的形式删除\nOwlPrinter v1.0.1\n\n\n\n".format(
                #             str(
                #                 time.strftime(
                #                     "%Y-%m-%d %H:%M:%S", time.localtime(time.time())
                #                 )
                #             )
                #         )
                #     )
                # print...
                return jsonify({"code": 200})
            elif "multipart/form-data" in request.content_type:
                img = request.files["file"].stream.read()
                if len(img) > 15 * 1024 * 1024:
                    return jsonify({
                        "code": 500,
                        "msg": "图片大于15M!"
                    })
                fileTp = filetype.guess(img)
                if fileTp is None:
                    return jsonify({"code": 500, "msg": "文件类型未知"})
                # if fileTp.extension not in ["jpg", "png"]:
                #     return jsonify({"code": 500})
                cups_conn.imageImproved(io.BytesIO(img))
                cups_conn.printTxt("\n\n")
                # print...
                # cups_conn.printTxt(
                #     "Finish at {}. \n您所上传的内容将会在打印完成后以不可逆的形式删除\nOwlPrinter v1.0.1\n\n\n\n".format(
                #         str(
                #             time.strftime(
                #                 "%Y-%m-%d %H:%M:%S", time.localtime(time.time())
                #             )
                #         )
                #     )
                # )
                return jsonify({"code": 200})
            else:
                print("error。文件类型不受支持")
                return jsonify({"code": 500, "msg": "文件类型未知"})
        else:
            if (
                request.remote_addr == "127.0.0.1"
                or not request.remote_addr.startswith("192.168")
            ):
                return jsonify({"code": 404})
            return jsonify({"code": 500})
    except Exception as e:
        traceback.print_exc(e)
        return jsonify({"code": 500, "msg": repr(e)})
    finally:
        cups_conn.close()


app.run("127.0.0.1", port=5582)
