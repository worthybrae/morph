import subprocess
import numpy as np
import cv2
from queue import Queue
import threading

def process_stream(input_url, output_queue, max_queue_size=30):
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

    try:
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

            # Check if we're falling behind
            if output_queue.qsize() > max_queue_size:
                # Skip some frames to catch up
                _ = process.stdout.read(frame_size * 5)  # Skip 5 frames
                print("Skipping frames to catch up")

    except Exception as e:
        print(f"Error processing frame: {e}")
    finally:
        process.terminate()
        print("Stream processing terminated")

def consume_frames(output_queue):
    while True:
        frame = output_queue.get()
        # Here you would typically do something with the frame,
        # like sending it over a network or saving it to disk.
        # For this example, we'll just print the frame size.
        print(f"Received frame of size: {len(frame)} bytes")

def main():
    input_url = 'https://cph-p2p-msl.akamaized.net/hls/live/2000341/test/master.m3u8'  # Replace with your m3u8 URL
    output_queue = Queue()

    # Start the stream processing in a separate thread
    processing_thread = threading.Thread(target=process_stream, args=(input_url, output_queue))
    processing_thread.start()

    # Start the frame consumer in the main thread
    consume_frames(output_queue)

if __name__ == "__main__":
    main()