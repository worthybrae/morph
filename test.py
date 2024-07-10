import cv2
import numpy as np
import subprocess
import threading
import time
import os
from http.server import HTTPServer, SimpleHTTPRequestHandler
from queue import Queue
from collections import deque

def get_dynamic_url():
    return f'https://videos-3.earthcam.com/fecnetwork/AbbeyRoadHD1.flv/chunklist_w.m3u8'

current_url = get_dynamic_url()

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

def format_headers(headers):
    header_str = ""
    for key, value in headers.items():
        header_str += f"{key}: {value}\r\n"
    return header_str

def update_url():
    global current_url
    while True:
        current_url = get_dynamic_url()
        time.sleep(60)

url_thread = threading.Thread(target=update_url, daemon=True)
url_thread.start()

def get_ffmpeg_input():
    formatted_headers = format_headers(headers)
    return [
        'ffmpeg',
        '-headers', formatted_headers,
        '-i', "https://videos-3.earthcam.com/fecnetwork/AbbeyRoadHD1.flv/chunklist_w.m3u8",
        '-f', 'rawvideo',
        '-pix_fmt', 'bgr24',
        '-s', '1280x720',
        '-'
    ]

os.makedirs('hls_output', exist_ok=True)

ffmpeg_output = [
    'ffmpeg',
    '-f', 'rawvideo',
    '-pix_fmt', 'bgr24',
    '-s', '1280x720',
    '-i', '-',
    '-c:v', 'libx264',
    '-preset', 'veryfast',
    '-tune', 'zerolatency',
    '-bf', '0',
    '-b:v', '2M',
    '-maxrate', '2.5M',
    '-bufsize', '2M',
    '-f', 'hls',
    '-r', '30',
    '-hls_list_size', '10',
    '-hls_flags', 'delete_segments+independent_segments',
    '-hls_segment_type', 'mpegts',
    '-hls_segment_filename', 'hls_output/segment_%d.ts',
    'hls_output/stream.m3u8'
]

frame_buffer = deque(maxlen=240)  # Buffer for 8 seconds of frames at 30 fps
processed_buffer = deque(maxlen=240)  # Buffer for processed frames

def process_frames():
    last_process_time = time.time()
    while True:
        current_time = time.time()
        if len(frame_buffer) > 0 and current_time - last_process_time >= 1/30:
            frame, timestamp = frame_buffer.popleft()
            edges = cv2.Canny(frame, 100, 200)
            output_frame = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
            processed_buffer.append((output_frame, timestamp))
            last_process_time = current_time
        else:
            time.sleep(0.001)


def restart_input_stream():
    global pipe_in
    if pipe_in:
        pipe_in.terminate()
    pipe_in = subprocess.Popen(get_ffmpeg_input(), stdout=subprocess.PIPE)

# Modify the FFmpeg output command
ffmpeg_output = [
    'ffmpeg',
    '-f', 'rawvideo',
    '-pix_fmt', 'bgr24',
    '-s', '1280x720',
    '-r', '30',
    '-i', '-',
    '-c:v', 'libx264',
    '-preset', 'ultrafast',
    '-tune', 'zerolatency',
    '-g', '150',
    '-keyint_min', '30',
    '-sc_threshold', '0',
    '-bf', '0',
    '-b:v', '2M',
    '-maxrate', '2.5M',
    '-bufsize', '2M',
    '-f', 'hls',
    '-hls_time', '5',
    '-hls_list_size', '5',
    '-hls_flags', 'delete_segments+independent_segments',
    '-hls_segment_type', 'mpegts',
    '-hls_segment_filename', 'hls_output/segment_%d.ts',
    'hls_output/stream.m3u8'
]

pipe_out = subprocess.Popen(ffmpeg_output, stdin=subprocess.PIPE)

pipe_in = None
restart_input_stream()

last_url_change = time.time()

class CORSRequestHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET')
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        super().end_headers()

def start_http_server():
    httpd = HTTPServer(('0.0.0.0', 8000), CORSRequestHandler)
    httpd.serve_forever()

http_thread = threading.Thread(target=start_http_server, daemon=True)
http_thread.start()

in_queue = Queue()
out_queue = Queue()

process_thread = threading.Thread(target=process_frames, daemon=True)
process_thread.start()

def write_output():
    last_write_time = time.time()
    while True:
        current_time = time.time()
        if len(processed_buffer) > 0 and current_time - last_write_time >= 1/30:  # Maintain 30 fps output
            output_frame = processed_buffer.popleft()
            pipe_out.stdin.write(output_frame[0].tobytes())
            last_write_time = current_time
        else:
            time.sleep(0.001)

write_thread = threading.Thread(target=write_output, daemon=True)
write_thread.start()

try:
    frame_count = 0
    start_time = time.time()
    while True:
        if time.time() - last_url_change >= 60:
            restart_input_stream()
            last_url_change = time.time()

        raw_frame = pipe_in.stdout.read(1280*720*3)
        if not raw_frame:
            time.sleep(0.001)
            continue

        frame = np.frombuffer(raw_frame, np.uint8).reshape((720, 1280, 3))
        timestamp = time.time()
        
        if len(frame_buffer) < frame_buffer.maxlen:
            frame_buffer.append((frame, timestamp))
        else:
            frame_buffer.popleft()
            frame_buffer.append((frame, timestamp))

        frame_count += 1
        elapsed_time = time.time() - start_time
        if elapsed_time >= 1:
            fps = frame_count / elapsed_time
            print(f"Input FPS: {fps:.2f}, Buffer: {len(frame_buffer)}, Processed: {len(processed_buffer)}")
            frame_count = 0
            start_time = time.time()

except KeyboardInterrupt:
    print("Stopping the stream...")
finally:
    if pipe_in:
        pipe_in.terminate()
    pipe_out.terminate()

def manage_segments():
    last_segment_time = 0
    while True:
        segments = sorted([f for f in os.listdir('hls_output') if f.endswith('.ts')])
        current_time = time.time()
        
        for segment in segments:
            segment_path = os.path.join('hls_output', segment)
            segment_mtime = os.path.getmtime(segment_path)
            
            if segment_mtime > last_segment_time:
                last_segment_time = segment_mtime
                # Process the segment if needed
                # Add your processing logic here
        
        # Delete old segments
        if len(segments) > 15:
            old_segments = segments[:-15]
            for old_segment in old_segments:
                os.remove(os.path.join('hls_output', old_segment))
        
        time.sleep(0.5)

# Start the segment management thread
segment_thread = threading.Thread(target=manage_segments, daemon=True)
segment_thread.start()
