import subprocess
import numpy as np
import cv2
import redis
import json
import time
import threading

def process_stream(input_url_container, redis_client, frame_ttl=30):
    ffmpeg_command = [
        'ffmpeg',
        '-i', input_url_container[0],
        '-f', 'rawvideo',
        '-pix_fmt', 'bgr24',
        '-vf', 'fps=30,scale=640:480',
        '-preset', 'fast',
        '-tune', 'zerolatency',
        '-r', '30',
        '-'
    ]

    process = subprocess.Popen(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    frame_counter = 0
    try:
        while True:
            frame_size = 640 * 480 * 3
            raw_frame = process.stdout.read(frame_size)

            if len(raw_frame) != frame_size:
                break

            frame = np.frombuffer(raw_frame, np.uint8).reshape((480, 640, 3))

            mask = np.zeros_like(frame)
            cv2.circle(mask, (320, 240), 100, (255, 255, 255), -1)
            masked_frame = cv2.bitwise_and(frame, mask)

            _, jpeg_frame = cv2.imencode('.jpg', masked_frame)
            
            # Store frame in Redis
            frame_key = f"frame:{frame_counter}"
            redis_client.setex(frame_key, frame_ttl, jpeg_frame.tobytes())
            
            # Update the latest frame index
            redis_client.set("latest_frame_index", frame_counter)
            
            frame_counter += 1

    except Exception as e:
        print(f"Error in stream processing: {e}")
        print("Attempting to reconnect in 5 seconds...")
        time.sleep(5)
    finally:
        if 'process' in locals():
            process.terminate()

def consume_frames(redis_client):
    last_processed_frame = -1
    while True:
        latest_frame_index = int(redis_client.get("latest_frame_index") or -1)
        
        if latest_frame_index > last_processed_frame:
            for frame_index in range(last_processed_frame + 1, latest_frame_index + 1):
                frame_key = f"frame:{frame_index}"
                frame_data = redis_client.get(frame_key)
                
                if frame_data:
                    # Here you would typically do something with the frame,
                    # like sending it over a network or saving it to disk.
                    print(f"Processed frame {frame_index}, size: {len(frame_data)} bytes")
                
            last_processed_frame = latest_frame_index
        
        time.sleep(0.03)  # Sleep for a short time to avoid busy-waiting

def monitor_frame_storage(redis_client):
    last_frame_count = 0
    stall_count = 0
    while True:
        total_keys = redis_client.dbsize()
        frame_keys = len(redis_client.keys('frame:*'))
        memory_usage = redis_client.info()['used_memory_human']
        
        print(f"Total keys: {total_keys}")
        print(f"Frame keys: {frame_keys}")
        print(f"Memory usage: {memory_usage}")

        if frame_keys == last_frame_count:
            stall_count += 1
        else:
            stall_count = 0
        
        if stall_count >= 5:  # No new frames for 25 seconds (5 * 5-second intervals)
            print("WARNING: No new frames detected for 25 seconds. Stream may have stalled.")
            # You could implement a restart mechanism here

        last_frame_count = frame_keys
        print("---")
        
        time.sleep(5)

def refresh_stream_url():
    return f"https://cph-p2p-msl.akamaized.net/hls/live/2000341/test/master.m3u8"

def refresh_stream(input_url_container):
    while True:
        time.sleep(60)  # Refresh every 60 seconds
        input_url_container[0] = refresh_stream_url()
        print(f"Refreshed stream URL: {input_url_container[0]}")

def main():
    input_url_container = [refresh_stream_url()]  # Initialize with the first URL
    redis_client = redis.Redis(host='localhost', port=6379, db=0)

    # Start the stream processing in a separate thread
    processing_thread = threading.Thread(target=process_stream, args=(input_url_container, redis_client))
    processing_thread.start()

    # Start the URL refresh in a separate thread
    refresh_thread = threading.Thread(target=refresh_stream, args=(input_url_container,))
    refresh_thread.start()

    monitoring_thread = threading.Thread(target=monitor_frame_storage, args=(redis_client,))
    monitoring_thread.start()

    # Start the frame consumer in the main thread
    consume_frames(redis_client)

if __name__ == "__main__":
    main()
