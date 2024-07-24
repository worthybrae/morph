import cv2
import numpy as np
import subprocess
import time
import datetime
import pytz
import matplotlib.colors as mcolors
from astral import LocationInfo
from astral.sun import sun
from numba import jit
from collections import defaultdict
import select


@jit(nopython=True)
def colorize(frame, background_color, line_color, height, width):
    colored_output = np.zeros((height, width, 3), dtype=np.uint8)
    for i in range(height):
        for j in range(width):
            if frame[i, j] == 0:
                colored_output[i, j, 0] = background_color[0]
                colored_output[i, j, 1] = background_color[1]
                colored_output[i, j, 2] = background_color[2]
            else:
                colored_output[i, j, 0] = line_color[0]
                colored_output[i, j, 1] = line_color[1]
                colored_output[i, j, 2] = line_color[2]
    return colored_output

def print_stats(stats):
    print("\n{:<20} {:>25} {:>20} {:>20}".format(
        "Operation", "Avg ± Std Dev", "% of Total", "% of Max Time"))
    print("-" * 90)

    total_avg = np.mean(stats['total'])
    max_time = 1/30 * 1e6  # 33333.33 us

    for k, v in stats.items():
        if k == 'get_frame':
            fv = [x for x in v if x <= 10000]
            avg = np.mean(fv)
            std = np.std(fv)
        elif k == 'waiting':

            avg = np.mean(v)
            avg_seconds = avg / 1e6
            print("{:<20} {:>10.6f}s".format(k, avg_seconds))
            continue
        else:
            avg = np.mean(v)
            std = np.std(v)
        percent_of_total = (avg / total_avg) * 100
        percent_of_max = (avg / max_time) * 100

        # Convert avg to seconds and std to microseconds
        avg_seconds = avg / 1e6
        std_microseconds = std

        print("{:<20} {:>10.6f}s ± {:>10.2f} us {:>18.2f}% {:>18.2f}%".format(
            k, avg_seconds, std_microseconds, percent_of_total, percent_of_max))
    
    print("-" * 90)

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
        '-i', 'https://videos-3.earthcam.com/fecnetwork/hdtimes10.flv/chunklist_w.m3u8',
        '-f', 'rawvideo',
        '-pix_fmt', 'gray',
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
        '-c:v', 'libx264',  # Use VideoToolbox for hardware-accelerated encoding
        '-b:v', '5000k',  # Set the video bitrate
        '-preset', 'fast',
        '-tune', 'zerolatency',
        '-f', 'hls',
        '-g', str(int(fps * 3)),
        '-hls_time', '3',
        '-hls_list_size', '5',
        '-hls_flags', 'delete_segments',
        '-hls_segment_filename', './tmp/hls/stream%03d.ts',
        '/tmp/hls/stream.m3u8'
    ]
    return subprocess.Popen(ffmpeg_command, stdin=subprocess.PIPE)

def process_frame(input_process, output_process, width, height, frame_count, stats):
    times = {'waiting': 0}

    start = time.time()
    frame = input_process.stdout.read(width * height)
    read_time = time.time() - start
    times['get_frame'] = min(read_time, .005)
    if times['get_frame'] == .005:
        times['waiting'] = read_time - .005

    start = time.time()
    background_color, line_color = get_colors()
    times['get_colors'] = time.time() - start

    start = time.time()
    array = np.frombuffer(frame, dtype=np.uint8).reshape((height, width))
    times['convert_array'] = time.time() - start

    start = time.time()
    edges = cv2.Canny(array, 100, 125, apertureSize=3, L2gradient=True)
    times['edges'] = time.time() - start

    start = time.time()
    colored_output = colorize(edges, background_color, line_color, height, width)
    times['colorize'] = time.time() - start

    start = time.time()
    output_process.stdin.write(colored_output.tobytes())
    times['send_output'] = time.time() - start

    times['total'] = times['get_frame'] + times['get_colors'] + times['convert_array'] + times['edges'] + times['colorize'] + times['send_output']
    
    # Update stats
    for k, v in times.items():
        stats[k].append(v * 1e6)  # Convert to microseconds

    # Print stats every 90 frames
    if frame_count % 90 == 0:
        print_stats(stats)
        stats.clear()
    
    return True
        
def main():
    # Specify global variables
    width = 640
    height = 480
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
    frame_count = 0
    stats = defaultdict(list)

    # Start running indefinite loop
    while True:
        try:
            input_process = initialize_ffmpeg_process(formatted_headers, width, height)
            output_process = initialize_output_ffmpeg_process(width, height, fps)
            while True:
                process_frame(input_process, output_process, width, height, frame_count, stats)
                frame_count += 1
                
        except Exception as e:
            print(f'Pipe broken: {e}')
            print(f'Attempting to recreate processes...')

            # Close existing processes if they're still running
            if 'input_process' in locals():
                input_process.terminate()
            if 'output_process' in locals():
                output_process.terminate()

            # Wait a bit before retrying
            time.sleep(3)

if __name__ == "__main__":
    main()
