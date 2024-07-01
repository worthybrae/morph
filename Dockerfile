# Use the jrottenberg/ffmpeg base image with alpine
FROM jrottenberg/ffmpeg:4.1-alpine

# Install Python3 and pip
RUN apk add --no-cache python3 py3-pip

# Install OpenCV and numpy
RUN pip3 install opencv-python-headless numpy

# Copy the Python script into the container
COPY stream_processor.py /usr/local/bin/stream_processor.py

# Set the entry point to run the Python script
ENTRYPOINT ["python3", "/usr/local/bin/stream_processor.py"]
