import cv2
import numpy as np
import subprocess
import time
import datetime
import pytz
import matplotlib.colors as mcolors
from astral import LocationInfo
from astral.sun import sun
import logging
from logging.handlers import RotatingFileHandler
import os
import multiprocessing


def find_midpoint(start_time, end_time):
    return start_time + (end_time - start_time) / 2

def get_color(progress, start_color, end_color, exponent=1):
    c1 = np.array(mcolors.hex2color(start_color))
    c2 = np.array(mcolors.hex2color(end_color))
    color = (1 - progress**exponent) * c1 + progress**exponent * c2
    return tuple(int(255 * x) for x in color)

def get_colors():
    london_tz = pytz.timezone('Europe/London')
    london_datetime = datetime.datetime.now(london_tz)
    london_old_datetime = datetime.datetime.now(london_tz) - datetime.timedelta(days=1)
    london_next_datetime = datetime.datetime.now(london_tz) + datetime.timedelta(days=1)

    london_date = london_datetime.date()
    london_old_date = london_old_datetime.date()
    london_next_date = london_next_datetime.date()

    city = LocationInfo(latitude=51.537052, longitude=-0.183325)
    s = sun(city.observer, date=london_date)
    y = sun(city.observer, date=london_old_date)
    n = sun(city.observer, date=london_next_date)

    old_dusk = y['dusk'].astimezone(london_tz)
    current_dawn = s['dawn'].astimezone(london_tz)
    old_midnight = find_midpoint(old_dusk, current_dawn)

    current_dusk = s['dusk'].astimezone(london_tz)
    current_sunrise = s['sunrise'].astimezone(london_tz)
    current_sunset = s['sunset'].astimezone(london_tz)
    current_noon = find_midpoint(current_sunrise, current_sunset)
    next_dawn = n['dawn'].astimezone(london_tz)
    current_midnight = find_midpoint(current_dusk, next_dawn)

    color_lookup = {
        'midnight': {
            'line': {
                'start': '#ced4da',
                'end': '#f8f9fa'
            },
            'background': {
                'start': '#6c757d',
                'end': '#212529',
            },
            'exponent': 0.25
        },
        'dawn': {
            'line': {
                'start': '#f8f9fa',
                'end': '#ced4da'
            },
            'background': {
                'start': '#212529',
                'end': '#6c757d'
            },
            'exponent': 4
        },
        'sunrise': {
            'line': {
                'start': '#ced4da',
                'end': '#6c757d'
            },
            'background': {
                'start': '#6c757d',
                'end': '#ced4da'
            },
            'exponent': 4
        },
        'afternoon': {
            'line': {
                'start': '#6c757d',
                'end': '#212529'
            },
            'background': {
                'start': '#ced4da',
                'end': '#f8f9fa'
            },
            'exponent': .25
        },
        'sunset': {
            'line': {
                'start': '#212529',
                'end': '#6c757d'
            },
            'background': {
                'start': '#f8f9fa',
                'end': '#ced4da'
            },
            'exponent': 4
        },
        'dusk': {
            'line': {
                'start': '#6c757d',
                'end': '#ced4da'
            },
            'background': {
                'start': '#ced4da',
                'end': '#6c757d'
            },
            'exponent': .25
        }
    }

    if london_datetime <= old_midnight:
        approaching = 'midnight' 
        progress = (london_datetime - old_dusk).seconds / (old_midnight - old_dusk).seconds
    elif london_datetime <= current_dawn:
        approaching = 'dawn'
        progress = (london_datetime - old_midnight).seconds / (current_dawn - old_midnight).seconds
    elif london_datetime <= current_sunrise:
        approaching = 'sunrise'
        progress = (london_datetime - current_dawn).seconds / (current_sunrise - current_dawn).seconds
    elif london_datetime <= current_noon:
        approaching = 'afternoon'
        progress = (london_datetime - current_sunrise).seconds / (current_noon - current_sunrise).seconds
    elif london_datetime <= current_sunset:
        approaching = 'sunset'
        progress = (london_datetime - current_noon).seconds / (current_sunset - current_noon).seconds
    elif london_datetime <= current_dusk:
        approaching = 'dusk'
        progress = (london_datetime - current_sunset).seconds / (current_dusk - current_sunset).seconds
    elif london_datetime <= current_midnight:
        approaching = 'midnight' 
        progress = (london_datetime - current_dusk).seconds / (current_midnight - current_dusk).seconds
    else:
        return None
    line_color = get_color(progress=progress, start_color=color_lookup[approaching]['line']['start'], end_color=color_lookup[approaching]['line']['end'], exponent=color_lookup[approaching]['exponent'])
    background_color = get_color(progress=progress, start_color=color_lookup[approaching]['background']['start'], end_color=color_lookup[approaching]['background']['end'], exponent=color_lookup[approaching]['exponent'])
    return background_color, line_color

def format_headers(headers):
    header_str = ""
    for key, value in headers.items():
        header_str += f"{key}: {value}\r\n"
    return header_str

def initialize_ffmpeg_process(headers, width, height):
    # Create FFmpeg command with custom headers
    ffmpeg_command = [
        'ffmpeg',
        '-headers', headers,
        '-i', 'https://videos-3.earthcam.com/fecnetwork/AbbeyRoadHD1.flv/chunklist_w.m3u8',
        '-f', 'rawvideo',
        '-pix_fmt', 'bgr24',
        '-s', f'{width}x{height}',
        '-'
    ]
    return subprocess.Popen(ffmpeg_command, stdout=subprocess.PIPE, bufsize=10**8)

def initialize_output_ffmpeg_process(width, height, fps):
    ffmpeg_command = [
        'ffmpeg',
        '-f', 'rawvideo',
        '-pix_fmt', 'bgr24',
        '-s', f'{width}x{height}',
        '-r', str(fps),
        '-i', '-',
        '-c:v', 'libx264',
        '-f', 'hls',
        '-g', str(int(fps * 6)),
        '-hls_time', '6',
        '-hls_list_size', '5',
        '-hls_flags', 'delete_segments',
        '-hls_segment_filename', '/tmp/hls/stream%03d.ts',
        '/tmp/hls/stream.m3u8'
    ]
    return subprocess.Popen(ffmpeg_command, stdin=subprocess.PIPE)

def process_frame(data):
    order, frame = data
    background_color, line_color = get_colors()
    # Blur the frame to get smoother edges
    blurred_frame = cv2.GaussianBlur(frame, (15, 15), 0)

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

    return order, background
        
def main():
    # Add a startup delay to ensure nginx is ready
    time.sleep(10)

    # Initialize logging setup
    log_file = '/usr/local/bin/logs/processor.log'
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    handler = RotatingFileHandler(log_file, maxBytes=10**7, backupCount=3)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # Specify global variables
    width = 1080
    height = 720
    fps = 30
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

    # Start running indefinite loop
    while True:
        logger.info("Starting input and output processes...")
        input_process = initialize_ffmpeg_process(formatted_headers, width, height)
        output_process = initialize_output_ffmpeg_process(width, height, fps)
        frame_size = width * height * 3  # width * height * 3 (for bgr24)
        pool = multiprocessing.Pool(processes=multiprocessing.cpu_count())
        while True:
            frames = [(i, np.frombuffer(input_process.stdout.read(frame_size), dtype=np.uint8).reshape((height, width, 3))) for i in range(180)]
            results = pool.map(process_frame, frames)
            results_sorted = sorted(results, key=lambda x: x[0])
            for r in results_sorted:
                # Write the transformed frame to the output process
                output_process.stdin.write(r[1].tobytes())

            
                

if __name__ == "__main__":
    main()
