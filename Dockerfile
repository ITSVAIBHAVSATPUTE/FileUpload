FROM ubuntu:22.04

# Install WINE and Python
RUN apt-get update && apt-get install -y \
    wine \
    python3 \
    python3-pip \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy files
COPY requirements.txt .
RUN pip3 install -r requirements.txt

# Copy your .exe file here
COPY checker.exe /app/
COPY bot.py /app/

# Create a virtual display for GUI apps (if needed)
ENV DISPLAY=:99
CMD Xvfb :99 -screen 0 1024x768x16 & python3 bot.py