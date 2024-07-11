# Use a Debian-based image with Python 3.9
FROM python:3.9-slim

# Install dependencies
RUN apt-get update && apt-get install -y \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && apt-get clean

# Copy the Python script into the container
COPY server.py /usr/local/bin/server.py

# Set the entry point to run the Python server script
ENTRYPOINT ["python3", "/usr/local/bin/server.py"]