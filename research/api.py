import cv2
import numpy as np
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import uvicorn
import requests
import time
import m3u8
import subprocess

app = FastAPI()

def fetch_m3u8_url():
    headers = {
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Connection': 'keep-alive',
        'Origin': 'https://www.abbeyroad.com',
        'Referer': 'https://www.abbeyroad.com/',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'cross-site',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'sec-ch-ua': '"Google Chrome";v="119", "Chromium";v="119", "Not?A_Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"'
    }
    m3u8_url = f"https://videos-3.earthcam.com/fecnetwork/AbbeyRoadHD1.flv/chunklist_w{int(time.time())}.m3u8"
    response = requests.get(m3u8_url, headers=headers)
    if response.status_code == 200:
        print("M3U8 content fetched successfully")
        print(response.text[:100])  # Print first 100 characters
        return response.text
    else:
        print(f"Failed to fetch M3U8 content. Status code: {response.status_code}")
        return None

def apply_mask(frame, mask):
    height, width = frame.shape[:2]
    circle_mask = np.zeros((height, width), np.uint8)
    cv2.circle(circle_mask, (width//2, height//2), min(height, width)//2, 255, -1)
    masked_frame = cv2.bitwise_and(frame, frame, mask=circle_mask)
    return masked_frame

def generate_frames():
    m3u8_content = fetch_m3u8_url()
    if m3u8_content is None:
        yield b'Error: Could not fetch M3U8 content'
        return

    m3u8_obj = m3u8.loads(m3u8_content)
    stream_url = m3u8_obj.segments[0].uri

    ffmpeg_cmd = [
        'ffmpeg',
        '-i', stream_url,
        '-f', 'rawvideo',
        '-pix_fmt', 'bgr24',
        '-vcodec', 'rawvideo',
        '-an', '-sn',
        '-'
    ]

    process = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

    while True:
        raw_frame = process.stdout.read(1920*1080*3)  # Adjust resolution if needed
        if not raw_frame:
            break

        frame = np.frombuffer(raw_frame, np.uint8).reshape((1080, 1920, 3))  # Adjust resolution if needed
        masked_frame = apply_mask(frame, None)
        
        ret, buffer = cv2.imencode('.jpg', masked_frame)
        frame = buffer.tobytes()
        
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.get("/video_feed")
async def video_feed():
    return StreamingResponse(generate_frames(), media_type="multipart/x-mixed-replace; boundary=frame")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)