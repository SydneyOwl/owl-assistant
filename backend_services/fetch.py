import hashlib
import flask
from flask_apscheduler import APScheduler
import requests
import time
import datetime
from flask_cors import CORS
import traceback
from dbtool import UsingMysql


def datadd(db,temperature,humidity):
    with UsingMysql() as um:
        um.cursor.execute("insert into `{}` (`temp`,`humi`,`time`) values ({},{},CURRENT_TIMESTAMP())".format(db,temperature,humidity))

def datadd_darkin(temperature,humidity,pm1,pm25,pm10,tvoc,co2):
    with UsingMysql() as um:
        um.cursor.execute("insert into `darkin_sensor` (`temp`,`humi`,`pm1`,`pm25`,`pm10`,`tvoc`,`co2`,`time`) values ({},{},{},{},{},{},{},CURRENT_TIMESTAMP())"
                          .format(temperature,humidity,pm1,pm25,pm10,tvoc,co2))


def fetchAllByDate(db,start,end):
    with UsingMysql() as um:
        sql = "SELECT * FROM {} WHERE `time` BETWEEN '{}' AND '{}' ORDER BY `time` ASC".format(db, start, end)
        return um.fetch_all(sql)

innersen = {
    "temp": "-",
    "humi": "-",
    "volt": "Nodata",
    "name": "Nodata",
    "rssi": "Nodata",
    "batt": "Nodata",
    "time": ".",
    "stamp": time.time(),
}
outersen = {
    "temp": "-",
    "humi": "-",
    "volt": "Nodata",
    "name": "Nodata",
    "rssi": "Nodata",
    "batt": "Nodata",
    "time": ".",
    "stamp": time.time(),
}
dksen = {
    "temp": "-",
    "humi": "-",
    "co2":"", 
    "pm1":"",
    "pm10":"",
    "pm25":"",
    "tvoc":"",
    "name": "darkin",
    "time": ".",
    "stamp": time.time(),
}

rev_db_add1_stamp = 0
rev_db_add2_stamp = 0
rev_db_adddksen_stamp = 0

app = flask.Flask(__name__)
CORS(app, resources=r"/*")

@app.before_request
def check_auth_header():
    # hidden
    return None

@app.route("/djsensor", methods=["GET"])
def fetchDJ():
    global dksen, rev_db_adddksen_stamp
    co2 = flask.request.args.get("co2")
    pm1 = flask.request.args.get("pm1")
    pm10 = flask.request.args.get("pm10")
    pm25 = flask.request.args.get("pm25")
    tvoc = flask.request.args.get("tvoc")
    temp = flask.request.args.get("temp")
    humi = flask.request.args.get("humi")
    try:
        dksen = {
            "temp": temp,
            "humi": humi,
            "co2":co2, 
            "pm1":pm1,
            "pm10":pm10,
            "pm25":pm25,
            "tvoc":tvoc,
            "name": "darkin",
            "time": time.asctime(time.localtime(time.time())),
            "stamp": time.time(),
        }
        
        if (time.time() - rev_db_adddksen_stamp > 600):
            datadd_darkin(temp,humi,pm1,pm25,pm10,tvoc,co2)
            rev_db_adddksen_stamp = time.time()
    except Exception as e:
        print(repr(e))
    finally:
        return "123"

@app.route("/sensors", methods=["GET", "POST"])
def fetchSensr():
    global innersen, outersen, rev_db_add1_stamp, rev_db_add2_stamp
    name = flask.request.args.get("name")
    temp = flask.request.args.get("temp")
    humi = flask.request.args.get("humi")
    batt = flask.request.args.get("bat")
    volt = flask.request.args.get("volt")
    rssi = flask.request.args.get("rssi")
    try:
        if name=="A4:C1:38:CF:B0:D6":
            innersen = {
                "temp": temp,
                "humi": humi,
                "volt": volt,
                "name": name,
                "rssi": rssi,
                "batt": batt,
                "time": time.asctime(time.localtime(time.time())),
                "stamp": time.time(),
            }

            if (time.time() - rev_db_add1_stamp > 600):
                datadd("inner_sensor",temp,humi)
                rev_db_add1_stamp = time.time()

        if name=="A4:C1:38:D5:05:79":
            outersen = {
                "temp": temp,
                "humi": humi,
                "volt": volt,
                "name": name,
                "rssi": rssi,
                "batt": batt,
                "time": time.asctime(time.localtime(time.time())),
                "stamp": time.time(),
            }
            if (time.time() - rev_db_add2_stamp > 600):
                datadd("out_sensor",temp,humi)
                rev_db_add2_stamp = time.time()
        requests.get(url="http://****/sensors?name={}&temp={}&humi={}&batt={}&volt={}&rssi={}".format(name,temp,humi,batt,volt,rssi),timeout=5)
    except Exception as e:
        print(repr(e))
    finally:
        return "123"


@app.route("/getSensor", methods=["GET"])
def getSens():
    return flask.jsonify([innersen, outersen, dksen])

@app.route("/getSensorDataByDateRange", methods=["POST"])
def getSenRage():
    dic = flask.request.get_json()
    db = dic["db"]
    startFrom = dic["start"]
    endFrom = dic["end"]
    result = fetchAllByDate(db, startFrom, endFrom)
    return flask.jsonify({"result":result})

app.run(host="0.0.0.0", port=3649)
