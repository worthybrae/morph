import cv2
import numpy as np
import subprocess
import time
from datetime import datetime

def get_dynamic_url():
    return f'https://videos-3.earthcam.com/fecnetwork/AbbeyRoadHD1.flv/chunklist_w{int(time.time())}.m3u8'

def format_headers(headers):
    header_str = ""
    for key, value in headers.items():
        header_str += f"{key}: {value}\r\n"
    return header_str

def initialize_ffmpeg_process(input_stream, headers, width, height, fps):
    # Create FFmpeg command with custom headers
    ffmpeg_command = [
        'ffmpeg',
        '-headers', headers,
        '-i', input_stream,
        '-f', 'rawvideo',
        '-pix_fmt', 'bgr24',
        '-s', f'{width}x{height}',
        '-r', str(fps),
        '-an',
        '-c:v', 'rawvideo',
        '-'
    ]
    return subprocess.Popen(ffmpeg_command, stdout=subprocess.PIPE, bufsize=10**8)

def initialize_output_ffmpeg_process(width, height, fps, output_stream):
    ffmpeg_command = [
        'ffmpeg',
        '-y',                        # Overwrite output files without asking
        '-f', 'rawvideo',            # Input format type
        '-pix_fmt', 'bgr24',         # Input pixel format
        '-s', f'{width}x{height}',   # Input size
        '-r', str(fps),              # Input frame rate
        '-i', '-',                   # Input comes from a pipe
        '-c:v', 'libx264',           # Video codec
        '-preset', 'fast',           # Encoding speed/quality tradeoff
        '-pix_fmt', 'yuv420p',       # Output pixel format
        '-f', 'flv',                 # Output format
        output_stream
    ]
    return subprocess.Popen(ffmpeg_command, stdin=subprocess.PIPE)

def process_frames(ffmpeg_process, output_process, buffer, width, height, fps):
    while True:
        # Read raw video frame from FFmpeg process
        raw_frame = ffmpeg_process.stdout.read(width * height * 3)
        if not raw_frame:
            print("Lost connection to stream, retrying...")
            break
        
        # Convert raw frame to numpy array
        frame = np.frombuffer(raw_frame, np.uint8).reshape((height, width, 3))
        
        # Convert frame to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        # Apply Canny edge detection
        edges = cv2.Canny(gray, 100, 200)
        # Convert edges to BGR format (three channels)
        frame = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
        
        # Append to buffer
        buffer.append(frame)
        
        # Ensure buffer size (6 seconds at 30fps)
        if len(buffer) > 180:
            buffer.pop(0)
        
        # Write the frame to the FFmpeg output process
        output_process.stdin.write(frame.tobytes())

def main():
    output_stream = 'rtmp://nginx:1935/live/stream'
    buffer = []

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

    formatted_headers = format_headers(headers)

    while True:
        input_stream = get_dynamic_url()
        print(input_stream)
        print(formatted_headers)
        # Initialize FFmpeg process to capture video with headers
        cap_process = initialize_ffmpeg_process(input_stream, formatted_headers, 640, 480, 30)
        width, height, fps = 640, 480, 30  # Modify these values as needed
        output_process = initialize_output_ffmpeg_process(width, height, fps, output_stream)

        start_time = time.time()

        while True:
            process_frames(cap_process, output_process, buffer, width, height, fps)

            # Check if the URL needs to be refreshed (6 seconds)
            if time.time() - start_time > 6:
                break

        cap_process.terminate()
        output_process.stdin.close()
        output_process.wait()

        # Output buffered frames to smooth transition
        for frame in buffer:
            output_process = initialize_output_ffmpeg_process(width, height, fps, output_stream)
            output_process.stdin.write(frame.tobytes())
            output_process.stdin.close()
            output_process.wait()

        time.sleep(5)  # Wait before retrying

if __name__ == "__main__":
    main()

