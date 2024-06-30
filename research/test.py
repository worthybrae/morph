import http.server
import socketserver
import threading
import subprocess
import numpy as np
import cv2


PORT = 8000

def get_video_dimensions():
    command = [
        'ffprobe',
        '-v', 'error',
        '-select_streams', 'v:0',
        '-show_entries', 'stream=width,height',
        '-of', 'csv=p=0',
        'https://cph-p2p-msl.akamaized.net/hls/live/2000341/test/master.m3u8'
    ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        dimensions = result.stdout.strip().split(',')
        width = int(dimensions[0])
        height = int(dimensions[1])
    except (IndexError, ValueError) as e:
        print(f"Error extracting video dimensions: {e}")
        width, height = 1972, 1080  # Fallback to default dimensions1972 × 1140
    return width, height

class MyHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "video/mp4")
        self.end_headers()

        command = [
            'ffmpeg',
            '-i', 'https://cph-p2p-msl.akamaized.net/hls/live/2000341/test/master.m3u8',
            '-c:v', 'copy',
            '-c:a', 'copy',
            '-bsf:a', 'aac_adtstoasc',
            '-f', 'mp4',
            '-movflags', 'frag_keyframe+empty_moov',
            'pipe:1'
        ]

        width = 1972
        height = 1140

        with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as proc:
            try:
                while True:
                    raw_frame = proc.stdout.read(width * height * 4)  # Read one frame (RGBA)
                    if not raw_frame:
                        break
                    print(len(raw_frame), type(raw_frame))
                    frame = np.frombuffer(raw_frame, np.uint8).reshape((height, width, 4))
                    print(type(frame))
                    # Now frame is an array of RGBA values
                    # Do any processing on the frame here

                    # For demonstration, convert frame back to BGR (OpenCV default) and display
                    frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGBA2BGR)
                    
                    print(type(frame_bgr))

                    frame_byt = frame_bgr.tobytes()
                    print(len(frame_byt), type(frame_byt))
                    self.wfile.write(raw_frame)
            except BrokenPipeError:
                proc.kill()
            except Exception as e:
                proc.kill()
                print(f"Error: {e}")

def run_server():
    with socketserver.TCPServer(("", PORT), MyHandler) as httpd:
        print(f"Serving at port {PORT}")
        httpd.serve_forever()

if __name__ == "__main__":
    server_thread = threading.Thread(target=run_server)
    server_thread.start()

    # Open the stream in the default web browser
    import webbrowser
    webbrowser.open(f'http://localhost:{PORT}')




