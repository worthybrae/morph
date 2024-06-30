import cv2
import numpy as np
from fastapi import FastAPI, Response
from fastapi.responses import StreamingResponse
import uvicorn

app = FastAPI()

# Function to apply mask to frame
def apply_mask(frame, mask):
    # Apply your mask logic here
    # This is a simple example that applies a circular mask
    height, width = frame.shape[:2]
    circle_mask = np.zeros((height, width), np.uint8)
    cv2.circle(circle_mask, (width//2, height//2), min(height, width)//2, 255, -1)
    masked_frame = cv2.bitwise_and(frame, frame, mask=circle_mask)
    return masked_frame

# Generator function for video streaming
def generate_frames():
    cap = cv2.VideoCapture(0)  # Use 0 for webcam or provide URL for IP camera
    while True:
        success, frame = cap.read()
        if not success:
            break
        else:
            # Apply mask to frame
            masked_frame = apply_mask(frame, None)  # Replace None with actual mask if needed
            
            # Encode frame to JPEG
            ret, buffer = cv2.imencode('.jpg', masked_frame)
            frame = buffer.tobytes()
            
            # Yield the frame in byte format
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.get("/video_feed")
async def video_feed():
    return StreamingResponse(generate_frames(), media_type="multipart/x-mixed-replace; boundary=frame")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
