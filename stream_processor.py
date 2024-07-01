import cv2
import numpy as np
import subprocess

# Define input and output streams
input_stream = 'https://cph-p2p-msl.akamaized.net/hls/live/2000341/test/master.m3u8'
output_stream = 'rtmp://nginx:1935/live/stream'

# Open the input stream with OpenCV
cap = cv2.VideoCapture(input_stream)

# Define the FFmpeg command to write to the output stream
ffmpeg_command = [
    'ffmpeg',
    '-y',
    '-f', 'rawvideo',
    '-pix_fmt', 'bgr24',
    '-s', '{}x{}'.format(int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))),
    '-r', str(cap.get(cv2.CAP_PROP_FPS)),
    '-i', '-',
    '-c:v', 'libx264',
    '-preset', 'fast',
    '-pix_fmt', 'yuv420p',
    '-f', 'flv',
    output_stream
]

# Start the FFmpeg process
process = subprocess.Popen(ffmpeg_command, stdin=subprocess.PIPE)

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    # Convert frame to grayscale
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    # Apply Canny edge detection
    edges = cv2.Canny(gray, 100, 200)
    # Convert edges to BGR format
    frame = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)

    # Write the frame to the FFmpeg process
    process.stdin.write(frame.tobytes())

# Release the video capture and close the FFmpeg process
cap.release()
process.stdin.close()
process.wait()
