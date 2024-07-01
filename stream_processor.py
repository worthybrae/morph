import cv2
import numpy as np
import subprocess
import time
from datetime import datetime, timedelta
import math


def get_dynamic_url():
    return f'https://videos-3.earthcam.com/fecnetwork/AbbeyRoadHD1.flv/chunklist_w{int(time.time())}.m3u8'

def calculate_sunrise_sunset(day_of_year, latitude=51.5074, longitude=-0.1278):
    # Approximate sunrise and sunset times based on the day of the year
    # This is a simplified version and not highly accurate
    # For London, UK
    days_from_solstice = day_of_year - 172
    if days_from_solstice < 0:
        days_from_solstice += 365
    
    sunset_hour = 18 - 2.5 * math.cos(math.radians(days_from_solstice * 360 / 365))
    sunrise_hour = 6 + 2.5 * math.cos(math.radians(days_from_solstice * 360 / 365))
    
    return sunrise_hour, sunset_hour

def get_colors():
    now = datetime.now()
    london_time = now + timedelta(hours=1)  # Adjusting to London time
    day_of_year = london_time.timetuple().tm_yday
    
    sunrise_hour, sunset_hour = calculate_sunrise_sunset(day_of_year)
    current_hour = london_time.hour + london_time.minute / 60.0

    if sunrise_hour <= current_hour <= sunset_hour:
        # Daytime
        if current_hour < (sunrise_hour + 1):  # Sunrise transition
            t = (current_hour - sunrise_hour) / 1.0
            background_color = (int(135 + t * 120), int(206 + t * 49), int(250 + t * 5))  # Light blue to almost white
            line_color = (int(255 - t * 55), int(255 - t * 104), int(255 - t * 245))  # Dark blue to almost black
        elif current_hour > (sunset_hour - 1):  # Sunset transition
            t = (current_hour - (sunset_hour - 1)) / 1.0
            background_color = (int(255 - t * 120), int(255 - t * 49), int(255 - t * 5))  # Almost white to light blue
            line_color = (int(200 + t * 55), int(151 + t * 104), int(10 + t * 245))  # Almost black to dark blue
        else:
            background_color = (255, 255, 255)  # Daytime light background
            line_color = (0, 0, 0)  # Daytime dark line
    else:
        # Nighttime
        if current_hour < (sunrise_hour - 1):  # Before sunrise transition
            t = (current_hour + 24 - (sunset_hour + 1)) / (24 - (sunset_hour + 1) + sunrise_hour)
            background_color = (int(15 + t * 120), int(15 + t * 49), int(30 + t * 5))  # Dark blue to light blue
            line_color = (int(240 - t * 55), int(240 - t * 104), int(240 - t * 245))  # Light color to dark color
        elif current_hour > (sunset_hour + 1):  # After sunset transition
            t = (current_hour - (sunset_hour + 1)) / (24 - (sunset_hour + 1) + sunrise_hour)
            background_color = (int(135 - t * 120), int(206 - t * 49), int(250 - t * 5))  # Light blue to dark blue
            line_color = (int(255 - t * 55), int(255 - t * 104), int(255 - t * 245))  # Dark color to light color
        else:
            background_color = (0, 0, 0)  # Nighttime dark background
            line_color = (255, 255, 255)  # Nighttime light line

    return background_color, line_color

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

def process_frames(ffmpeg_process, output_process, buffer, width, height, background_color, line_color):
    while True:
        # Read raw video frame from FFmpeg process
        raw_frame = ffmpeg_process.stdout.read(width * height * 3)
        if not raw_frame:
            print("Lost connection to stream, retrying...")
            break
        
        # Convert raw frame to numpy array
        frame = np.frombuffer(raw_frame, np.uint8).reshape((height, width, 3))
        # Blur the frame to get smoother edges
        blurred_frame = cv2.GaussianBlur(frame, (11, 11), 0)
        # Convert frame to grayscale
        gray = cv2.cvtColor(blurred_frame, cv2.COLOR_BGR2GRAY)
        # Apply Canny edge detection
        edges = cv2.Canny(gray, 300, 400, apertureSize=5)
        # Smooth edges again
        kernel = np.ones((2, 2), np.uint8)  # Adjust kernel size as needed
        smoothed_edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)

        # Create a background and apply edge color
        background = np.full_like(frame, background_color)
        background[smoothed_edges > 0] = line_color
        
        # Append to buffer
        buffer.append(background)
        
        # Ensure buffer size (6 seconds at 30fps)
        if len(buffer) > 180:
            buffer.pop(0)
        
        # Write the frame to the FFmpeg output process
        output_process.stdin.write(background.tobytes())

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
        background_color, line_color = get_colors()
        # Initialize FFmpeg process to capture video with headers
        cap_process = initialize_ffmpeg_process(input_stream, formatted_headers, 640, 480, 30)
        width, height, fps = 640, 480, 30  # Modify these values as needed
        output_process = initialize_output_ffmpeg_process(width, height, fps, output_stream)

        start_time = time.time()

        while True:
            process_frames(cap_process, output_process, buffer, width, height, background_color, line_color)

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

