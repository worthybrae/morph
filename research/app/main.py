from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.lifespan import Lifespan
import asyncio
import queue
from process_stream import start_processing_thread

app = FastAPI()

input_url = "https://cph-p2p-msl.akamaized.net/hls/live/2000341/test/master.m3u8"  # Replace with your M3U8 URL
output_queue = queue.Queue(maxsize=540)

@app.on_event("startup")
async def startup_event():
    start_processing_thread(input_url, output_queue)

async def video_streamer():
    frame_interval = 1 / 30  # Frame interval in seconds (for 30fps)
    next_frame_time = asyncio.get_event_loop().time() + frame_interval

    while True:
        try:
            frame = output_queue.get(timeout=1)
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        except queue.Empty:
            continue  # Skip the frame if the queue is empty

        await asyncio.sleep(max(0, next_frame_time - asyncio.get_event_loop().time()))
        next_frame_time += frame_interval

@app.get("/video")
async def video_feed():
    return StreamingResponse(video_streamer(), media_type='multipart/x-mixed-replace; boundary=frame')

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

