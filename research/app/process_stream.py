import cv2
import numpy as np
import subprocess
import threading
import queue

def process_stream(input_url, output_queue):
    # FFmpeg command to fetch the M3U8 stream and output raw video frames
    ffmpeg_command = [
        'ffmpeg',
        '-i', input_url,
        '-f', 'rawvideo',
        '-pix_fmt', 'bgr24',
        '-vf', 'fps=30,scale=640:480',  # Set frame rate and scale
        '-preset', 'fast',  # Use fast preset for quicker processing
        '-tune', 'zerolatency',  # Minimize latency for live streaming
        '-r', '30',  # Ensure output frame rate is 30 fps
        '-'
    ]

    process = subprocess.Popen(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    while True:
        # Read raw video frame data from FFmpeg
        frame_size = 640 * 480 * 3  # width * height * channels
        raw_frame = process.stdout.read(frame_size)

        if len(raw_frame) != frame_size:
            break

        # Convert the raw frame to a numpy array
        frame = np.frombuffer(raw_frame, np.uint8).reshape((480, 640, 3))

        # Apply a mask to the frame (example: create a circular mask)
        mask = np.zeros_like(frame)
        cv2.circle(mask, (320, 240), 100, (255, 255, 255), -1)
        masked_frame = cv2.bitwise_and(frame, mask)

        # Encode the frame as JPEG
        _, jpeg_frame = cv2.imencode('.jpg', masked_frame)

        # Put the processed frame into the queue
        output_queue.put(jpeg_frame.tobytes())

def start_processing_thread(input_url, output_queue):
    processing_thread = threading.Thread(target=process_stream, args=(input_url, output_queue))
    processing_thread.daemon = True
    processing_thread.start()

