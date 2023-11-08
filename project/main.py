from celery.result import AsyncResult
from fastapi import Body, FastAPI, Form, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from worker import create_task,task_call_api


app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")



@app.get("/")
def home(request: Request):
    return templates.TemplateResponse("home.html", context={"request": request})


@app.post("/tasks", status_code=201)
def run_task(payload = Body(...)):
    task_type = payload["type"]
    task = create_task.delay(int(task_type))
    return JSONResponse({"task_id": task.id})


@app.get("/tasks/{task_id}")
def get_status(task_id):
    task_result = AsyncResult(task_id)
    result = {
        "task_id": task_id,
        "task_status": task_result.status,
        "task_result": task_result.result
    }
    return JSONResponse(result)

@app.post("/tasks/{task_id}")
def get_status(task_id):
    task_result = AsyncResult(task_id)
    result = {
        "task_id": task_id,
        "task_status": task_result.status,
        "task_result": task_result.result
    }
    return JSONResponse(result)


import cv2
import requests
from io import BytesIO

from blob_detector import detect_blobs
from getting_lines import get_staffs
from note import *
from photo_adjuster import adjust_photo

import numpy as np
import wave
import json


@app.post("/test_ai", status_code=201)
def test_ai(payload: dict = Body(...)):
    # URL của hình ảnh bạn muốn đọc
    id_product = payload.get("id_product")
    url = payload.get("url")
    user_id = payload.get("user_id")
    image_url = url

    # Tải hình ảnh từ URL sử dụng thư viện requests
    response = requests.get(image_url)
    image_data = BytesIO(response.content)
    image_array = np.asarray(bytearray(image_data.read()), dtype=np.uint8)

    # Đọc hình ảnh bằng OpenCV
    image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

    adjusted_photo = adjust_photo(image)
    staffs = get_staffs(adjusted_photo)
    blobs = detect_blobs(adjusted_photo, staffs)
    notes = extract_notes(blobs, staffs, adjusted_photo)
    pitch = draw_notes_pitch(adjusted_photo, notes)
    print(pitch)
    violin_f = {"A0": 27.50,"Bb0": 29.14,"B0": 30.87,"C1": 32.70,"Db1": 34.65,"D1": 36.71,"Eb1": 38.89,"E1": 41.20,
                "F1": 43.65,"Gb1": 46.25,"G1": 49.00,"Ab1": 51.91,"A1": 55.00,"Bb1": 58.27,"B1": 61.74,"C2": 65.41,
                "Db2": 69.30,"D2": 73.42,"Eb2": 77.78,"E2": 82.41,"F2": 87.31,"Gb2": 92.50,"G2": 98.00,"Ab2": 103.83,
                "A2": 110.00,"Bb2": 116.54,"B2": 123.47,"C3": 130.81,"Db3": 138.59,"D3": 146.83,"Eb3": 155.56,
                "E3": 164.81,"F3": 174.61,"Gb3": 185.00,"G3": 196.00,"Ab3": 207.65,"A3": 220.00,"Bb3": 233.08,
                "B3": 246.94,"C4": 261.63,"Db4": 277.18,"D4": 293.66,"Eb4": 311.13,"E4": 329.63,"F4": 349.23,
                "Gb4": 369.99,"G4": 392.00,"Ab4": 415.30,"A4": 440.00,"Bb4": 466.16,"B4": 493.88,"C5": 523.25,
                "Db5": 554.37,"D5": 587.33,"Eb5": 622.25,"E5": 659.26,"F5": 698.46,"Gb5": 739.99,"G5": 783.99,
                "Ab5": 830.61,"A5": 880.00,"Bb5": 932.33,"B5": 987.77,"C6": 1046.50,"Db6": 1108.73,"D6": 1174.66,
                "Eb6": 1244.51,"E6": 1318.51,"F6": 1396.92,"Gb6": 1479.98,"G6": 1567.98,"Ab6": 1661.22,"A6": 1760.00,
                "Bb6": 1864.66,"B6": 1975.53,"C7": 2093.00,"Db7": 2217.46,"D7": 2349.32,"Eb7": 2489.02,"E7": 2637.02,
                "F7": 2793.83,"Gb7": 2959.96,"G7": 3135.96,"Ab7": 3322.44,"A7": 3520.00,"Bb7": 3729.31,"B7": 3951.07,"C8": 4186.01,}
    # Thời gian phát âm thanh cho mỗi phím (trong mili giây)
    duration = 1000  # 1 giây

    piano_frequencies = pitch

    # Tạo và lưu âm thanh cho mỗi phím
    samples = []
    for frequency in piano_frequencies:
        t = np.linspace(0, duration / 1000, int(44100 * duration / 1000), endpoint=False)
        sample = 0.5 * np.sin(2 * np.pi * violin_f[frequency] * t)

        # Chuyển bước sóng thành dạng 16-bit signed PCM
        sample = (sample * 32767).astype(np.int16)
        samples.append(sample)

    # Ghi âm thanh vào tệp WAV
    with wave.open('piano_notes.wav', 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(44100)
        for sample in samples:
            wf.writeframes(sample.tobytes())
    
    # Đường dẫn API bạn muốn gửi yêu cầu POST tới
    api_url = 'https://serverltmnc.onrender.com/upload/video'

    # Đường dẫn của tệp WAV bạn muốn tải lên
    wav_file_path = 'piano_notes.wav'

    # Tạo một đối tượng form-data
    files = {'file': ('audio.wav', open(wav_file_path, 'rb'), 'audio/wav')}

    # Gửi yêu cầu POST với dữ liệu form-data
    response = requests.post(api_url, files=files)
    # Kiểm tra kết quả
    if response.status_code == 200:
        print('Tệp đã được tải lên thành công.')
        data = response.json()
        # Địa chỉ URL của API
        api_url = 'https://serverltmnc.onrender.com/product/update/'+id_product

        # Dữ liệu JSON bạn muốn truyền
        data = {
            "img_link":url,
            "audio_link":data['url'],
            "user_id":user_id
        }

        # Sử dụng thư viện json.dumps() để chuyển đổi dữ liệu thành chuỗi JSON
        json_data = json.dumps(data)

        # Đặt tiêu đề 'Content-Type' là 'application/json'
        headers = {'Content-Type': 'application/json'}

        # Gửi yêu cầu POST với dữ liệu JSON trong body
        res = requests.put(api_url, data=json_data, headers=headers)
        # Kiểm tra kết quả
        if res.status_code == 200:
            result = res.json()
            print(result)
            return JSONResponse(result)
        else:
            print('Lỗi:', res.status_code)
            return JSONResponse({"error": res.status_code})
        
    else:
        print('Lỗi trong quá trình gửi yêu cầu.')
        return JSONResponse({"Error":'Lỗi trong quá trình gửi yêu cầu.'})
    

@app.post("/tasks_train_ai", status_code=201)
def tasks_train_ai(payload = Body(...)):
    task_id_product = payload.get("id_product")
    task_url = payload["img_link"]
    task_user_id = payload["user_id"]
    print(task_user_id,task_url)
    task = task_call_api.delay(task_id_product,task_user_id,task_url)
    print(task)
    task_result = AsyncResult(task.id)
    result = {
        "task_id": task.id,
        "task_status": task_result.status,
        "task_result": task_result.result
    }
    return JSONResponse(result)