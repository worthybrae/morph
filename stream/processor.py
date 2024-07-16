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
import multiprocessing
from functools import partial


@jit(nopython=True)
def colorize_gradient(gradient, background_color, line_color, height, width):
    colored_output = np.zeros((height, width, 3), dtype=np.uint8)
    for i in range(height):
        for j in range(width):
            if gradient[i, j] == 0:
                colored_output[i, j, 0] = background_color[0]
                colored_output[i, j, 1] = background_color[1]
                colored_output[i, j, 2] = background_color[2]
            else:
                colored_output[i, j, 0] = line_color[0]
                colored_output[i, j, 1] = line_color[1]
                colored_output[i, j, 2] = line_color[2]
    return colored_output

def print_time_stats(time_data, write_time, total_time, batch_size=90, max_time=3):
    """
    Print statistics for timing data, including write time.
    
    :param time_data: List of dictionaries, each containing timing information for a frame
    :param write_time: Time taken to write the batch to output
    :param batch_size: Number of frames in the batch (default 90)
    :param max_time: Maximum allowed time for processing (default 3 seconds)
    """
    # Combine all dictionaries
    all_times = {key: [] for key in time_data[0].keys()}
    for frame_time in time_data:
        for key, value in frame_time.items():
            all_times[key].append(value)

    # Calculate total time for each frame
    total_times = [sum(frame.values()) for frame in time_data]

    print(f"\nTiming statistics for batch of {batch_size} frames:")
    print(f"{'Operation':<15} {'Avg (s)':<10} {'Std Dev (s)':<12} {'% of Total':<12} {'% of Max Time':<15}")
    print("-" * 70)

    for operation, times in all_times.items():
        avg_time = np.mean(times)
        std_dev = np.std(times)
        percent_of_total = (avg_time / (np.mean(total_times) + write_time / batch_size)) * 100
        percent_of_max = (avg_time / max_time) * 100

        print(f"{operation:<15} {avg_time:<10.6f} {std_dev:<12.6f} {percent_of_total:<12.2f} {percent_of_max:<15.2f}")

    # Add write time
    avg_write_time = write_time / batch_size  # Average write time per frame
    percent_of_total_write = (avg_write_time / (np.mean(total_times) + avg_write_time)) * 100
    percent_of_max_write = (avg_write_time / max_time) * 100
    print(f"{'write':<15} {avg_write_time:<10.6f} {'N/A':<12} {percent_of_total_write:<12.2f} {percent_of_max_write:<15.2f}")

    print("-" * 70)
    total_avg = np.mean(total_times) + avg_write_time / 90
    total_std = np.std(total_times)  # Note: This doesn't include write time variability
    print(f"{'Per Frame':<15} {total_avg:<10.6f} {total_std:<12.6f} 100.00        {(total_avg / max_time) * 100:<15.2f}")
    print(f"{'Total':<15} {total_time:<10.6f} ({(total_time / max_time) * 100:<15.2f}% of total time)")

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
        '-hls_list_size', '10',
        '-hls_flags', 'delete_segments',
        '-hls_segment_filename', '/tmp/hls/stream%03d.ts',
        '/tmp/hls/stream.m3u8'
    ]
    return subprocess.Popen(ffmpeg_command, stdin=subprocess.PIPE)

def process_frame(order, frame, read_time, width, height, lookup_table):
    times = {'read': read_time}

    start = time.time()
    background_color, line_color = get_colors()
    times['get_colors'] = time.time() - start

    start = time.time()
    blurred_image = cv2.blur(frame, (5, 5))
    times['blur'] = time.time() - start

    start = time.time()
    emphasized_darker = cv2.LUT(blurred_image, lookup_table) # Apply the gamma correction using the lookup table
    times['darker'] = time.time() - start

    start = time.time()
    edges = cv2.Canny(emphasized_darker, 1175, 1200, apertureSize=5)
    times['edges'] = time.time() - start

    start = time.time()
    kernel = np.array([
        [0, 1, 0, 0, 0],
        [1, 0, 0, 0, 0],
        [0, 0, 0, 0, 0],
        [0, 0, 0, 0, 1],
        [0, 0, 0, 1, 0]], dtype=np.uint8)
    gradient = cv2.morphologyEx(edges, cv2.MORPH_GRADIENT, kernel)
    times['dilate'] = time.time() - start

    start = time.time()
    colored_output = colorize_gradient(gradient, background_color, line_color, height, width)
    times['colorize'] = time.time() - start
    return order, colored_output.tobytes(), times
        
def main():
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
    gamma = 0.5  # Gamma value less than 1
    inv_gamma = 1.0 / gamma
    # Build a lookup table mapping pixel values [0, 255] to their adjusted gamma values
    lookup_table = np.array([((i / 255.0) ** inv_gamma) * 255 for i in range(256)], dtype=np.uint8)

    # Start running indefinite loop
    pool = multiprocessing.Pool(processes=multiprocessing.cpu_count())
    
    while True:
        try:
            input_process = initialize_ffmpeg_process(formatted_headers, width, height)
            output_process = initialize_output_ffmpeg_process(width, height, fps)
            
            while True:
                starting_time = time.time()
                frames = []
                for i in range(90):
                    start = time.time()
                    frame = input_process.stdout.read(width * height)
                    if len(frame) < width * height:
                        # Handle the error - maybe wait and retry, or restart the stream
                        print('\n\nincomplete frame\n\n')
                        break

                    array = np.frombuffer(frame, dtype=np.uint8).reshape((height, width))
                    read_time = time.time() - start
                    frames.append((i, array, read_time, width, height, lookup_table))
                
                if len(frames) > 0:

                    results = pool.starmap(process_frame, frames)
                    results.sort(key=lambda x: x[0])  # Ensure correct order

                    time_data = [result[2] for result in results]
                    
                    start_write = time.time()
                    output_process.stdin.write(b''.join([result[1] for result in results]))
                    write_time = time.time() - start_write

                    total_time = time.time() - starting_time

                    print_time_stats(time_data, write_time, total_time)

        except Exception as e:
            print(f'Pipe Broken: {e}')


if __name__ == "__main__":
    main()
