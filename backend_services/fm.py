import hashlib
import os
import queue
import time
import requests
from lxml import etree
import re
from datetime import datetime, timedelta
import wave
import pyaudio
import threading
import random
from time import sleep, time as curTime
import flask
from flask_cors import CORS
import numpy
import ser

station_addr = "http://xxx"
info_addr = station_addr + "/thermal/fetchATIS"

cur_path = "/home/sydneycat/fm/tranz"
gen_file = cur_path + "/wavgen/tmp.wav"
cache_file = cur_path + "/wavgen/cache.wav"
char_path = cur_path + "/char/"
num_path = cur_path + "/number/"
sent_path = cur_path + "/sentence/"
unit_path = cur_path + "/unit/"
add_path = cur_path + "/addition/"

CHUNK = 1024

atis_volume = 100
music_volume = 100

stop_music = False
stop_atis = False

current_song = ""
song_queue = queue.Queue(-1)

app = flask.Flask(__name__)
CORS(app, resources=r"/*")

SERIAL_PORT = "/dev/ttyUSB0"

ser.setPrt(SERIAL_PORT)

ser.create()

@app.before_request
def check_auth_header():
    # hidden
    return None


@app.route("/fm/volume", methods=["GET", "POST"])
def fm():
    global music_volume, atis_volume
    data = flask.request.get_json()
    status = data["status"]
    target = data["target"]
    if target == "music":
        music_volume = max(0, min(100, int(status)))  # 限制范围
    if target == "atis":
        atis_volume = max(0, min(100, int(status)))  # 限制范围
    return flask.jsonify(
        {
            "code": 200
        }
    )


@app.route("/fm/curVol", methods=["POST"])
def fm2():
    songList = os.listdir(add_path)
    return flask.jsonify(
        {
            "atis": atis_volume,
            "totalSong": songList,
            "music": music_volume,
            "currentSong": current_song,
            "stopATIS": stop_atis,
            "stopMusic": stop_music,
        }
    )


@app.route("/fm/chgSong", methods=["POST"])
def fm4():
    data = flask.request.get_json()
    targetSong = data["song"]
    song_queue.put(targetSong)
    return flask.jsonify(
        {
            "code": 200
        })


@app.route("/fm/control", methods=["GET", "POST"])
def fm1():
    global stop_music, stop_atis, music_thread, atis_thread
    data = flask.request.get_json()
    target = data["target"]
    status = data["status"]
    if target == "music":
        stop_music = False if status == "on" else True
        if (not stop_music) and not music_thread.is_alive():
            music_thread = threading.Thread(target=main_music)
            music_thread.start()
    if target == "atis":
        stop_atis = False if status == "on" else True
        if (not stop_atis) and not atis_thread.is_alive():
            atis_thread = threading.Thread(target=main_atis)
            atis_thread.start()
    return flask.jsonify(
        {
            "code": 200
        })


@app.route("/fm/rec", methods=["GET", "POST"])
def fm5():
    f = flask.request.files["file"]
    print("Recv: "+ f.name+" with size" + str(f.content_length))
    f.save(add_path + "temp.wav")
    song_queue.put("temp.wav")
    return ""


@app.route("/fm/modifyFM", methods=["POST"])
def cfm():
    global stop_music, stop_atis
    data = flask.request.get_json()
    operation = data["instruction"]
    value = data["targetM"]
    # if value != "" and not str.isdigit(value):
    #     return flask.jsonify({"code": 100})
    
    if operation == "openPower":
        return flask.jsonify({"code": 200, "result": ser.open_power()})
    if operation == "closePower":
        return flask.jsonify({"code": 200, "result": ser.close_power()})
    if operation == "startBlink":
        return flask.jsonify({"code": 200, "result": ser.blink(float(value), True)})
    if operation == "endBlink":
        return flask.jsonify({"code": 200, "result": ser.blink(float(value), False)})
    if operation == "writeText":
        return flask.jsonify({"code": 200, "result": ser.write_text(value)})
    
    res = ser.get_pwr_on()
    if operation == "isopen":
        if (not res): 
            stop_atis = True
            stop_music = True 
        return flask.jsonify({"code": 200, "result": res})
    
    if not res:
        return flask.jsonify({"code": 0})
    if operation == "setVolume":
        return flask.jsonify({"code": 200, "result": ser.set_volume(int(value))})
    elif operation == "setFrequency":
        return flask.jsonify({"code": 200, "result": ser.set_freq(int(value))})
    elif operation == "setBacklight":
        return flask.jsonify({"code": 200, "result": ser.set_backlight(int(value))})
    elif operation == "setCampus":
        return flask.jsonify({"code": 200, "result": ser.set_campus(int(value))})
    elif operation == "getCurrent":
        return flask.jsonify({"code": 200, "result": ser.get_current()})
    elif operation == "reset":
        return flask.jsonify({"code": 200, "result": ser.reset()})
    else:
        return flask.jsonify({"code": 300})

def playsound(playtype, location):
    try:
        f = wave.open(location, "rb")
    except Exception:
        f = wave.open(unit_path + "empty.wav", "rb")
    
    p = pyaudio.PyAudio()
    
    # 根据位宽度确定格式
    sample_width = f.getsampwidth()
    if sample_width == 1:
        numpy_format = numpy.int8
        pyaudio_format = pyaudio.paInt8
    elif sample_width == 2:
        numpy_format = numpy.int16
        pyaudio_format = pyaudio.paInt16
    elif sample_width == 4:
        numpy_format = numpy.int32
        pyaudio_format = pyaudio.paInt32
    else:
        numpy_format = numpy.int16
        pyaudio_format = pyaudio.paInt16
    
    stream = p.open(
        format=pyaudio_format,
        channels=f.getnchannels(),
        rate=f.getframerate(),
        output=True,
    )
    
    CHUNK = 1024
    data = f.readframes(CHUNK)
    
    while len(data) > 0:
        vol = 100
        if playtype == "atis":
            while stop_atis:
                sleep(0.2)
            vol = atis_volume
        if playtype == "music":
            while stop_music:
                sleep(0.2)
            if not song_queue.empty():
                break
            vol = music_volume
        
        sound_level = vol / 100.0
        
        # 根据位深度处理数据
        if sample_width == 1:  # 8位
            chunk = numpy.frombuffer(data, numpy.int8)
            chunk = (chunk * sound_level).astype(numpy.int8)
        elif sample_width == 2:  # 16位
            chunk = numpy.frombuffer(data, numpy.int16)
            chunk = (chunk * sound_level).astype(numpy.int16)
        elif sample_width == 4:  # 32位
            chunk = numpy.frombuffer(data, numpy.int32)
            chunk = (chunk * sound_level).astype(numpy.int32)
        else:
            chunk = numpy.frombuffer(data, numpy.int16)
            chunk = (chunk * sound_level).astype(numpy.int16)
        
        stream.write(chunk.tobytes())
        data = f.readframes(CHUNK)
    
    sleep(0.2)
    stream.stop_stream()
    stream.close()
    p.terminate()
    f.close()  # 确保关闭文件


def fetch_station_status():
    try:
        station_info = requests.post(info_addr)
    except Exception as e:
        print(repr(e))
        return {}
    if station_info.json()["code"] != 200:
        return {}
    return station_info.json()


def add_sentence(lan, seq, seq_wav: list[str]):
    prefix = "cl"
    if lan == "en":
        prefix = "el"
    seq_wav.append(sent_path + prefix + str(seq) + ".wav")


def add_number(lan, num: str, seq_wav: list[str]) -> None:
    prefix = ""
    if lan == "cn":
        prefix = "c"
    for i in str(num):
        if num == ".":
            num = "dec"
        seq_wav.append(num_path + prefix + i + ".wav")


def add_char(chr, seq_wav: list[str]):
    for i in str.lower(chr):
        seq_wav.append(char_path + i + ".wav")


def add_unit(lan, unit, seq_wav: list[str]):
    prefix = ""
    if lan == "cn":
        prefix = "chn_"
    seq_wav.append(unit_path + prefix + unit + ".wav")


def add_space(nsec, seq_wav: list[str]):
    seq_wav.append(str(nsec))


def gen_wav_list(lan, station: dict, metar: dict) -> list[str]:
    seq_wav = []
    now_time = datetime.now()
    utc_time = now_time - timedelta(hours=8)  # 减去8小时
    utc_fmt_time = utc_time.strftime("%H%M")
    utc_hour = utc_time.strftime("%H").lstrip("0")

    infolist = [chr(i) for i in range(97, 123)]
    
    if utc_hour == "":
        utc_hour=0

    information = infolist[int(utc_hour) % 24]

    # Eng
    # Information
    add_sentence(lan, 1, seq_wav)
    add_space(5, seq_wav)
    add_char(information, seq_wav)
    add_space(10, seq_wav)
    # UTC
    if lan == "cn":
        add_sentence(lan, 2, seq_wav)
        add_space(5, seq_wav)
        add_number(lan, utc_fmt_time, seq_wav)
    if lan == "en":
        add_number(lan, utc_fmt_time, seq_wav)
        add_space(5, seq_wav)
        add_sentence(lan, 2, seq_wav)
    if metar == {}:
        add_unit(lan, "failed_metar", seq_wav)
        add_space(5, seq_wav)
    if station == {}:
        add_unit(lan, "failed_workstation", seq_wav)
        add_space(5, seq_wav)
    if metar != {} and station != {}:
        # NO_ERROR
        add_sentence(lan, 3, seq_wav)
    add_space(10, seq_wav)
    if station != {}:
        # UPTIME
        uptime = station["data"]["terminal"]["general"]["Uptime"]
        cctime = re.findall(r"[1-9]+\.?[0-9]*", uptime)
        str_uptime = ""
        for i in cctime:
            str_uptime += i
        add_sentence(lan, 4, seq_wav)
        add_space(5, seq_wav)
        add_number(lan, str_uptime, seq_wav)
        add_space(10, seq_wav)
        # WORKSTATION TEMPERATURE
        add_sentence(lan, 5, seq_wav)
        add_space(5, seq_wav)
        add_number(lan, int(float(station["data"]["terminal"]["temp"])), seq_wav)
        add_space(10, seq_wav)
        # SENSOR
        add_sentence(lan, 6, seq_wav)
        add_space(10, seq_wav)
        # SENSOR 1
        # TEMP
        add_sentence(lan, 7, seq_wav)
        add_space(5, seq_wav)
        stemp = station["data"]["sensor"]["sensor1"]["temp"]
        if stemp == "-":
            add_unit(lan, "unknown", seq_wav)
        else:
            add_number(lan, int(float(stemp)), seq_wav)
        add_space(10, seq_wav)
        # HUM
        add_sentence(lan, 8, seq_wav)
        add_space(5, seq_wav)
        shumi = station["data"]["sensor"]["sensor1"]["hum"]
        if shumi == "-":
            add_unit(lan, "unknown", seq_wav)
        else:
            add_number(lan, int(float(shumi)), seq_wav)
        add_space(10, seq_wav)
        # SENSOR 2
        # TEMP
        add_sentence(lan, 9, seq_wav)
        add_space(5, seq_wav)
        stemp = station["data"]["sensor"]["sensor2"]["temp"]
        if stemp == "-":
            add_unit(lan, "unknown", seq_wav)
        else:
            add_number(lan, int(float(stemp)), seq_wav)
        add_space(10, seq_wav)
        # HUM
        add_sentence(lan, 10, seq_wav)
        add_space(5, seq_wav)
        shumi = station["data"]["sensor"]["sensor2"]["hum"]
        if shumi == "-":
            add_unit(lan, "unknown", seq_wav)
        else:
            add_number(lan, int(float(shumi)), seq_wav)
        add_space(10, seq_wav)
    # METAR
    if metar != {}:
        add_sentence(lan, 11, seq_wav)
        add_space(10, seq_wav)
        # TEMPERATURE
        add_sentence(lan, 12, seq_wav)
        add_space(5, seq_wav)
        add_number(lan, metar["temp"], seq_wav)
        add_space(10, seq_wav)
        # DEW
        add_sentence(lan, 13, seq_wav)
        add_space(5, seq_wav)
        add_number(lan, metar["dew"], seq_wav)
        add_space(5, seq_wav)
        # WINDSPEED
        add_sentence(lan, 14, seq_wav)
        add_space(5, seq_wav)
        add_number(lan, metar["windspeed"], seq_wav)
        add_unit(lan, "mprs", seq_wav)
        add_space(10, seq_wav)
        # WINDDIRECTION
        add_sentence(lan, 15, seq_wav)
        add_space(5, seq_wav)
        if not str.isdigit(metar["winddirection"]):
            for i in metar["winddirection"]:
                add_char(i, seq_wav)
        else:
            add_number(lan, metar["winddirection"], seq_wav)
            add_unit(lan, "deg", seq_wav)
        add_space(10, seq_wav)
        # VISIBILITY
        add_sentence(lan, 16, seq_wav)
        add_space(5, seq_wav)
        if metar["vis"] == "9999":
            add_unit(lan, "above10km", seq_wav)
        elif metar["vis"] == "CAVOK":
            add_unit(lan, "cavok", seq_wav)
        else:
            add_number(lan, metar["vis"], seq_wav)
            add_unit(lan, "meters", seq_wav)
        add_space(10, seq_wav)
        # QNH
        add_sentence(lan, 17, seq_wav)
        add_space(5, seq_wav)
        add_number(lan, metar["qnh"], seq_wav)
        add_space(10, seq_wav)
    # FIL
    add_sentence(lan, 18, seq_wav)
    add_char(information, seq_wav)
    # add_space(5, seq_wav)
    return seq_wav


def read_wav(file_path):
    if not os.path.exists(file_path):
        file_path = unit_path + "empty.wav"
    wav = wave.open(file_path, "rb")
    params = wav.getparams()
    frames = wav.readframes(wav.getnframes())
    wav.close()
    return params, frames


def merge_wav(wav_list, output_file):
    merged_params = None
    merged_frames = b""
    params = None
    for file in wav_list:
        if str.isdigit(file):
            # pass
            for _ in range(int(file)):
                params, frames = read_wav(unit_path + "empty.wav")
                merged_frames += frames
        else:
            params, frames = read_wav(file)
            merged_frames += frames
    if merged_params is None:
        merged_params = params
    merged_wav = wave.open(output_file, "wb")
    merged_wav.setparams(merged_params)
    merged_wav.writeframes(merged_frames)
    merged_wav.close()


def gen_wav(station, metar, declear):
    en = gen_wav_list("en", station, metar)
    cn = gen_wav_list("cn", station, metar)
    if declear:
        # add_sentence("cn",19,cn)
        # add_sentence("en",19,en)
        pass
    add_space(30, cn)
    cn += en
    merge_wav(cn, gen_file)


def generate_atis(declear = False):
    metar = fetch_METAR()
    station = fetch_station_status()
    gen_wav(station, metar, declear)


def main_ann_freq():
    global atis_volume,music_volume
    sleep(3)
    tmp1,tmp2 = atis_volume,music_volume
    atis_volume = 30
    music_volume = 30
    seq = []
    curr_freq = ser.get_current()["fre"]
    add_sentence("cn",19,seq)
    add_number("cn",str(curr_freq),seq)
    add_sentence("cn",20,seq)
    add_space(3,seq)
    add_sentence("en",19,seq)
    add_number("en",str(curr_freq),seq)
    add_sentence("en",20,seq)
    merge_wav(seq,cache_file)
    playsound("other", cache_file)
    atis_volume,music_volume = tmp1,tmp2


def main_atis():
    global stop_atis
    try:
        print("atis thread started.")
        generate_atis()
        now = int(curTime())
        while True:
            if int(curTime()) - now > 15 * 60:
                now = int(curTime())
                generate_atis()
            playsound("atis", gen_file)
            sleep(3)
    except Exception as e:
        stop_atis = True
        print(repr(e))
    finally:
        print("atis thread exited.")


def main_music():
    global current_song, stop_music
    file_list = os.listdir(add_path)
    try:
        print("music thread started.")
        while True:
            result = random.choice(file_list)
            while not song_queue.empty():
                result = song_queue.get()
            current_song = result
            playsound("music", add_path + result)
    except Exception as e:
        stop_music = True
        print(repr(e))
    finally:
        print("music thread exited.")


# a = threading.Thread(target=lambda:ps(add_path + "1.wav"))
# a.start()
# print(fetch_METAR())
music_thread = threading.Thread(target=main_music)
atis_thread = threading.Thread(target=main_atis)  # ()
# main_ann_freq()
music_thread.start()
atis_thread.start()
app.run("127.0.0.1", port=9352)
# a.join()
# b.join()
