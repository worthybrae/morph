import cv2
import numpy as np
import requests
import time

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
        return response.text
    else:
        return None

def capture_stream():
    m3u8_content = fetch_m3u8_url()
    if not m3u8_content:
        print("Failed to fetch M3U8 content.")
        return

    video = cv2.VideoCapture(m3u8_content)
    while video.isOpened():
        ret, frame = video.read()
        if not ret:
            break

        processed_frame = apply_mask(frame)
        yield processed_frame  # Yield each frame to the caller

    video.release()

def apply_mask(frame):
    height, width, _ = frame.shape
    overlay = np.zeros((height, width, 4), dtype='uint8')

    # Example mask: a red semi-transparent square
    cv2.rectangle(overlay, (50, 50), (200, 200), (0, 0, 255, 100), -1)
    return cv2.addWeighted(frame, 1, overlay, 0.4, 0)
