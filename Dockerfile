# Use a Debian-based image with Python 3.8
FROM python:3.9-slim

# Install FFmpeg and dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsm6 \
    libxext6 \
    libxrender-dev \
    build-essential \
    cmake \
    && apt-get clean

# Upgrade pip to the latest version
RUN pip install --upgrade pip

# Copy requirement file into the docker container
COPY prod_requirements.txt .

# Install any dependencies specified in requirements.txt
RUN pip install --no-cache-dir -r prod_requirements.txt

RUN mkdir -p /logs && chmod -R 777 /logs

# Copy the Python script into the container
COPY stream_processor.py /usr/local/bin/stream_processor.py

# Set the entry point to run the Python script
ENTRYPOINT ["python3", "/usr/local/bin/stream_processor.py"]
