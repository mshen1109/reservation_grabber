# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV HEADLESS=true

# Install system dependencies (Chrome and tools)
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Chromium and Chromium Driver (works on ARM64/Apple Silicon and AMD64)
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    vim \
    && rm -rf /var/lib/apt/lists/*

# Set environment variable for Chromium usage
ENV CHROME_BINARY_LOCATION=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

# Set work directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy the current directory contents into the container at /app
COPY . /app/

# Create a non-root user
RUN useradd -m myuser

# Create chrome_profile directory and set permissions
RUN mkdir -p /app/chrome_profile && chown -R myuser:myuser /app/chrome_profile

# Change ownership of the application directory to myuser
RUN chown -R myuser:myuser /app

USER myuser

# Command to run the script
# We'll default to reservation_browser.py but this can be overridden
CMD ["python", "reservation_browser.py"]
