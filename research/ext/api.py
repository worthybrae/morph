import cv2
import numpy as np
import subprocess
import threading
import queue
import logging
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import io

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = FastAPI()

output_queue = queue.Queue(maxsize=180)  # Assuming you want to keep 180 frames
processing_thread = None
FRAME_RATE = 30
FRAME_INTERVAL = 1.0 / FRAME_RATE

def process_stream(input_url, output_queue):
    logging.info(f"Starting FFmpeg process for URL: {input_url}")
    ffmpeg_command = [
        'ffmpeg',
        '-i', input_url,
        '-f', 'rawvideo',
        '-pix_fmt', 'bgr24',
        '-vf', 'fps=30,scale=640:480',
        '-preset', 'fast',
        '-tune', 'zerolatency',
        '-r', '30',
        '-'
    ]

    process = subprocess.Popen(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    logging.info("FFmpeg process started")

    try:
        while True:
            frame_size = 640 * 480 * 3
            raw_frame = process.stdout.read(frame_size)

            if len(raw_frame) != frame_size:
                logging.warning("Incomplete frame read, exiting")
                break

            frame = np.frombuffer(raw_frame, np.uint8).reshape((480, 640, 3))

            mask = np.zeros_like(frame)
            cv2.circle(mask, (320, 240), 100, (255, 255, 255), -1)
            masked_frame = cv2.bitwise_and(frame, mask)

            _, jpeg_frame = cv2.imencode('.jpg', masked_frame)
            if output_queue.full():
                output_queue.get()  # Remove the oldest frame
            output_queue.put(jpeg_frame.tobytes())
            logging.info("Frame processed and added to queue")
    except Exception as e:
        logging.error(f"Error during processing: {e}")
    finally:
        process.terminate()
        logging.info("FFmpeg process terminated")

def check_for_new_segment(input_url, output_queue):
    while True:
        process_stream(input_url, output_queue)
        logging.info("Checking for new segments")
        time.sleep(2)  # Check every 2 seconds for new segments

@asynccontextmanager
async def lifespan(app: FastAPI):
    global processing_thread
    input_url = "your_input_stream_url"  # Replace with your actual input URL
    processing_thread = threading.Thread(target=check_for_new_segment, args=(input_url, output_queue))
    processing_thread.daemon = True
    processing_thread.start()
    logging.info("Processing thread started")
    yield
    processing_thread.join()  # Ensure the thread is cleaned up on shutdown
    logging.info("Processing thread terminated")

app = FastAPI(lifespan=lifespan)

def generate_frames():
    while True:
        start_time = time.time()
        if not output_queue.empty():
            frame = output_queue.get()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        else:
            logging.info("No frames available, waiting")
        elapsed_time = time.time() - start_time
        time_to_wait = FRAME_INTERVAL - elapsed_time
        if time_to_wait > 0:
            time.sleep(time_to_wait)
        else:
            logging.warning("Frame processing took longer than frame interval")

@app.get("/get-frame/")
async def get_frame():
    return StreamingResponse(generate_frames(), media_type="multipart/x-mixed-replace; boundary=frame")

# Run the FastAPI app
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
