# Bartels Micropump Docker Solution
# This approach uses Docker to create a Linux environment with USB passthrough

FROM ubuntu:22.04

# Install required packages
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    udev \
    libusb-1.0-0 \
    libusb-1.0-0-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages
RUN pip3 install pyusb pyserial

# Create working directory
WORKDIR /app

# Copy pump control scripts
COPY . .

# Set environment variables for USB access
ENV PYTHONUNBUFFERED=1

# Create script to install the pybartelslabtronix library
RUN pip3 install pybartelslabtronix

# Default command to run pump test
CMD ["python3", "test_pump_docker.py"]
