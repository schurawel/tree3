FROM python:3.12.3-slim

# Install system dependencies for PyQt6, build tools, and git
RUN apt-get update && apt-get install -y \
    qt6-base-dev \
    libgl1-mesa-glx \
    # Core XCB libraries
    libxcb1 \
    libxcb-keysyms1 \
    libxcb-image0 \
    libxcb-shm0 \
    libxcb-icccm4 \
    libxcb-sync1 \
    libxcb-xfixes0 \
    libxcb-shape0 \
    libxcb-randr0 \
    libxcb-render-util0 \
    libxcb-util1 \
    libxcb-glx0 \
    # Previously identified XCB dependencies
    libxcb-xinerama0 \
    libxkbcommon-x11-0 \
    libxcb-cursor0 \
    # Other system libraries
    libdbus-1-3 \
    libpulse0 \
    libasound2 \
    libasound2-plugins \
    libxslt1.1 \
    # Additional common QtWebEngine dependencies
    libnss3 \
    libfontconfig1 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libxfixes3 \
    libxrender1 \
    libxi6 \
    libgbm1 \
    libxkbfile1 \
    # More comprehensive list of potential dependencies
    libfreetype6 \
    libharfbuzz0b \
    libicu72 \
    libjpeg62-turbo \
    libpng16-16 \
    libxml2 \
    libsqlite3-0 \
    libevent-2.1-7 \
    # Fontconfig and common fonts (including for icons/symbols)
    fontconfig \
    fonts-noto-core \
    fonts-noto-color-emoji \
    fonts-freefont-ttf \
    # For multimedia capabilities in QtWebEngine
    libavcodec59 \
    libavformat59 \
    libavutil57 \
    libvpx7 \
    libopus0 \
    libwebp7 \
    libopenjp2-7 \
    # For X11 testing/accessibility extensions, sometimes needed
    libxtst6 \
    # End of additional dependencies
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/* \
    && fc-cache -fv \
    && ldconfig

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Compile Python files to bytecode (.pyc)
# This will create __pycache__ directories with .pyc files
RUN python -m compileall .

# Create a symlink to make code compatible with venv-specific paths
# This helps if your code has hardcoded .venv paths
RUN ln -s /usr/local /app/.venv

# Set environment variable for display and Xauthority
ENV DISPLAY=:0
ENV XAUTHORITY=/root/.Xauthority

# Set the entry point
CMD ["python", "main.py"]