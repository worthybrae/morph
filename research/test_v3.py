import cv2
import numpy as np
import subprocess
import re
import os

# URL of the input HLS stream
input_hls_url = 'https://videos-3.earthcam.com/fecnetwork/AbbeyRoadHD1.flv/chunklist_w.m3u8'
# Output HLS stream URL (local server)
output_hls_url = 'stream.m3u8'

# Custom headers to be passed into the input stream
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

def format_headers():
    header_str = ""
    for key, value in headers.items():
        header_str += f"{key}: {value}\r\n"
    return header_str

# FFmpeg command to read the HLS stream
ffmpeg_input_cmd = [
    'ffmpeg',
    '-headers', format_headers(),
    '-i', input_hls_url,
    '-f', 'rawvideo',
    '-pix_fmt', 'bgr24',
    '-s', '1280x720',
    '-'
]

# FFmpeg command to write the processed frames to HLS
ffmpeg_output_cmd = [
    'ffmpeg',
    '-f', 'rawvideo',
    '-pix_fmt', 'bgr24',
    '-s', '1280x720',  # set frame size
    '-r', '30',  # frame rate
    '-i', '-',
    '-c:v', 'libx264',
    '-preset', 'veryfast',
    '-f', 'hls',
    '-hls_time', '3',
    '-hls_list_size', '5',
    '-hls_flags', 'delete_segments',
    output_hls_url
]

# Start the input and output FFmpeg processes
input_proc = subprocess.Popen(ffmpeg_input_cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
output_proc = subprocess.Popen(ffmpeg_output_cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)

try:
    while True:
        # Read a frame from the input stream
        in_bytes = input_proc.stdout.read(1280 * 720 * 3)
        if not in_bytes:
            break
        
        # Convert bytes to numpy array
        frame = np.frombuffer(in_bytes, np.uint8).reshape((720, 1280, 3))
        
        # Apply edge detection
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 100, 200)
        edges_colored = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
        
        # Write the processed frame to the output stream
        output_proc.stdin.write(edges_colored.tobytes())

finally:
    input_proc.stdout.close()
    output_proc.stdin.close()
    input_proc.wait()
    output_proc.wait()
