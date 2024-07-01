# Use the jrottenberg/ffmpeg base image with alpine
FROM jrottenberg/ffmpeg:4.1-alpine

# Install Python3, pip, and necessary build tools
RUN apk add --no-cache python3 py3-pip build-base python3-dev

# Use pre-built wheels for numpy and opencv-python-headless
RUN pip3 install --no-cache-dir numpy opencv-python-headless

# Copy the Python script into the container
COPY stream_processor.py /usr/local/bin/stream_processor.py

# Set the entry point to run the Python script
ENTRYPOINT ["python3", "/usr/local/bin/stream_processor.py"]



