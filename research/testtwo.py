import streamlink
import vlc
import threading
import time
import os
import tempfile
import subprocess

class M3U8Player:
    def __init__(self, url):
        self.url = url
        self.streams = streamlink.streams(url)
        self.best_stream = self.streams['best']
        self.temp_dir = tempfile.mkdtemp()
        self.temp_file = os.path.join(self.temp_dir, 'stream.m3u8')
        self.ffmpeg_log_file = os.path.join(self.temp_dir, 'ffmpeg_log.txt')
        self.vlc_instance = vlc.Instance()
        self.player = self.vlc_instance.media_player_new()

    def update_stream(self):
        while True:
            with open(self.ffmpeg_log_file, 'w') as log_file:
                print(f"Running FFmpeg, logging to {self.ffmpeg_log_file}")
                stream_process = subprocess.Popen(
                    ['ffmpeg', '-i', self.best_stream.url, '-c', 'copy', '-f', 'hls', self.temp_file],
                    stdout=log_file, stderr=log_file
                )
                stream_process.communicate()
            print(f"Updated stream file at {self.temp_file}")
            time.sleep(10)  # Update interval

    def play(self):
        print(f"Attempting to play stream from {self.temp_file}")
        media = self.vlc_instance.media_new(self.temp_file)
        self.player.set_media(media)
        self.player.play()

    def run(self):
        update_thread = threading.Thread(target=self.update_stream)
        update_thread.daemon = True
        update_thread.start()
        self.play()
        while True:
            time.sleep(1)

if __name__ == "__main__":
    url = 'https://cph-p2p-msl.akamaized.net/hls/live/2000341/test/master.m3u8'
    player = M3U8Player(url)
    player.run()



