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
COPY requirements.txt .

# Create logs directory
RUN mkdir -p /usr/local/bin/logs

# Install any dependencies specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the Python script into the container
COPY processor.py /usr/local/bin/processor.py

# Set the entry point to run the Python script
ENTRYPOINT ["python3", "/usr/local/bin/processor.py"]