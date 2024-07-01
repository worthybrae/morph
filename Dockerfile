# Use the jrottenberg/ffmpeg base image with alpine
FROM jrottenberg/ffmpeg:4.1-alpine

# Install Python3, pip, and necessary build tools
RUN apk add --no-cache python3 py3-pip cmake ninja build-base

# Install OpenCV and numpy using pre-built wheels
RUN pip3 install numpy
RUN pip3 install opencv-python-headless

# Copy the Python script into the container
COPY stream_processor.py /usr/local/bin/stream_processor.py

# Set the entry point to run the Python script
ENTRYPOINT ["python3", "/usr/local/bin/stream_processor.py"]


