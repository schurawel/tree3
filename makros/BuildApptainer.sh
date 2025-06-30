#!/bin/bash

# BuildApptainer.sh - Creates an Apptainer container for ResearchGuide
# Author: Based on the ResearchGuide application by Jason A. Schurawel

set -e  # Exit immediately if a command exits with a non-zero status

# Define variables
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "${SCRIPT_DIR}")"
CONTAINERS_DIR="${PROJECT_DIR}/containers"
CONTAINER_NAME="researchguide_app"
DEF_FILE="${CONTAINERS_DIR}/researchguide.def"
SIF_FILE="${CONTAINERS_DIR}/researchguide.sif"
DATA_DIR="${CONTAINERS_DIR}/apptainer_data"

echo "===== ResearchGuide Apptainer Container Builder ====="

# Create containers directory if it doesn't exist
mkdir -p "${CONTAINERS_DIR}"
echo "✓ Containers directory: ${CONTAINERS_DIR}"

# Check if Apptainer is installed
if ! command -v apptainer &> /dev/null; then
    echo "Error: Apptainer is not installed. Please install Apptainer first."
    echo "Visit: https://apptainer.org/docs/admin/main/installation.html"
    exit 1
fi

echo "✓ Apptainer detected: $(apptainer --version)"

# Ensure data directory exists
mkdir -p "${DATA_DIR}"

# Create the Apptainer definition file using Docker bootstrap
echo "Creating Apptainer definition file using Docker bootstrap..."
cat > "${DEF_FILE}" << EOF
Bootstrap: docker
From: ubuntu:22.04

%setup
    # Copy files from host to container during bootstrap
    mkdir -p \${SINGULARITY_ROOTFS}/app
    cp -r ${PROJECT_DIR}/main.py \${SINGULARITY_ROOTFS}/app/
    cp -r ${PROJECT_DIR}/requirements.txt \${SINGULARITY_ROOTFS}/app/
    cp -r ${PROJECT_DIR}/ResearchGuideUnearth \${SINGULARITY_ROOTFS}/app/

%post
    # Set non-interactive installation to avoid prompts
    export DEBIAN_FRONTEND=noninteractive
    export TZ=Europe/London  # Set a default timezone

    # First, install just the essential base packages to ensure proper locale setup
    apt-get update && apt-get install -y locales tzdata
    
    # Manually set up locales without relying on locale-gen command
    echo "en_US.UTF-8 UTF-8" >> /etc/locale.gen
    
    # Try standard locale-gen first
    if command -v locale-gen >/dev/null 2>&1; then
        locale-gen en_US.UTF-8
    else
        # Alternative method if locale-gen command isn't available
        echo "locale-gen not found, using alternative method"
        # On Ubuntu, locales are often in /usr/sbin/locale-gen
        if [ -x "/usr/sbin/locale-gen" ]; then
            /usr/sbin/locale-gen en_US.UTF-8
        else
            # Last resort fallback - create empty locale dir and set default
            mkdir -p /usr/lib/locale
            echo "LC_ALL=C.UTF-8" > /etc/default/locale
            echo "LANG=C.UTF-8" >> /etc/default/locale
        fi
    fi

    update-locale LANG=en_US.UTF-8
    
    # Now install all the other dependencies with critical X11 libraries first
    apt-get update && apt-get install -y --no-install-recommends \
        libx11-dev \
        libxext-dev \
        libxrender-dev \
        libxrandr-dev \
        libxfixes-dev \
        libxcomposite-dev \
        libxcursor-dev \
        libxdamage-dev \
        libxkbcommon-dev \
        libxkbcommon-x11-dev \
        libx11-xcb-dev \
        libxcb1-dev \
        libxcb-keysyms1-dev \
        libxcb-image0-dev \
        libxcb-shm0-dev \
        libxcb-icccm4-dev \
        libxcb-xfixes0-dev \
        libxcb-shape0-dev \
        libxcb-randr0-dev \
        libxcb-render-util0-dev \
        libxcb-glx0-dev \
        libxcb-xinerama0-dev \
        libxcb-dri3-dev \
        libxcb-present-dev \
        libxcb-xkb-dev \
        libxcb-xinput-dev \
        libxcb-xinerama0-dev \
        libxcb-cursor0 \
        libxcb-xkb1 \
        libxkbcommon-x11-0 \
        libxcb-xinerama0 \
        libxcb-xinput0 \
        libx11-xcb-dev libglu1-mesa-dev libxrender-dev libxi-dev libxkbcommon-dev libxkbcommon-x11-dev \
        libx11-xcb1 \
        libxcb-dri3-0 \
        libxcb-present0 \
        python3 \
        python3-pip \
        python3-dev \
        xauth \
        build-essential \
        cmake \
        git \
        libgl1-mesa-glx \
        qt6-base-dev \
        apt-utils \
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
        libxcb-xinerama0 \
        libnss3 \
        libnspr4 \
        libasound2 \
        libasound2-plugins \
        libxslt1.1 \
        libxcomposite1 \
        libxdamage1 \
        libxtst6 \
        libxrandr2 \
        libegl1 \
        libxfixes3 \
        libxrender1 \
        libxi6 \
        libgbm1 \
        libxkbfile1 \
        libxkbcommon0 \
        libpulse0 \
        libdbus-1-3 \
        libfontconfig1 \
        libfreetype6 \
        libxext6 \
        libx11-6 \
        libharfbuzz0b \
        libicu70 \
        libjpeg-turbo8 \
        libpng16-16 \
        libxml2 \
        libsqlite3-0 \
        libevent-2.1-7 \
        fontconfig \
        fonts-noto-core \
        fonts-noto-color-emoji \
        fonts-freefont-ttf \
        libavcodec58 \
        libavformat58 \
        libavutil56 \
        libvpx7 \
        libopus0 \
        libwebp7 \
        libopenjp2-7 \
        x11-apps \
        mesa-utils \
        ca-certificates && apt-get clean && rm -rf /var/lib/apt/lists/*
    
    # Ensure critical libraries are installed with their recommended dependencies
    # Qt 6.5.0+ specifically requires libxcb-cursor0 for the xcb platform plugin.
    # Other libraries like libxkbcommon, libgl1, libfontconfig1, libdbus-1-3,
    # and various xcb libraries also benefit from having their recommended
    # dependencies for full functionality with Qt.
    apt-get update && apt-get install -y \
        libxcb-cursor0 \
        libxkbcommon-x11-0 \
        libxkbcommon0 \
        libgl1 \
        libfontconfig1 \
        libdbus-1-3 \
        libxcb-glx0 \
        libxcb-image0 \
        libxcb-keysyms1 \
        libxcb-randr0 \
        libxcb-render-util0 \
        libxcb-render0 \
        libxcb-shape0 \
        libxcb-shm0 \
        libxcb-sync1 \
        libxcb-xfixes0 \
        libxcb-xinerama0 \
        libxcb-xkb1 \
        libxcb-icccm4 \
        libxcb-util1
    
    # Create /usr/bin/python symlink to python3
    if [ -x "/usr/bin/python3" ]; then
        echo "Python3 found at /usr/bin/python3. Creating symlink /usr/bin/python."
        ln -sf /usr/bin/python3 /usr/bin/python
        # Verify python symlink works
        /usr/bin/python --version || echo "Warning: python symlink created but verification failed"
    else
        echo "WARNING: /usr/bin/python3 not found, trying to locate python3 elsewhere..."
        # Try alternative locations
        for possible_path in /bin/python3 /usr/local/bin/python3; do
            if [ -x "$possible_path" ]; then
                echo "Python3 found at $possible_path. Creating symlink /usr/bin/python."
                ln -sf "$possible_path" /usr/bin/python
                # Verify python symlink works
                /usr/bin/python --version && break
            fi
        done
        
        # If we still don't have python, install it again as a last resort
        if [ ! -x "/usr/bin/python" ]; then
            echo "Reinstalling Python as a last resort..."
            apt-get update && apt-get install -y python3
            if [ -x "/usr/bin/python3" ]; then
                ln -sf /usr/bin/python3 /usr/bin/python
            else
                echo "ERROR: Cannot find python3 after reinstallation"
                exit 1
            fi
        fi
    fi

    # Set up application directory
    cd /app
    
    # Install Python dependencies including PyQt6 (not available via apt)
    python3 -m pip install --no-cache-dir --upgrade pip setuptools wheel
    # Install PyQt6 with all required components
    python3 -m pip install --no-cache-dir PyQt6 PyQt6-Qt6 PyQt6-WebEngine PyQt6-sip
    python3 -m pip install --no-cache-dir -r requirements.txt

    # Reinstall x11-apps to ensure xdpyinfo is correctly installed
    apt-get install -y --reinstall x11-apps
    
    # Create directories for persistent data
    mkdir -p /data/cache /data/config /data/output
    chmod 777 /data /data/cache /data/config /data/output

    # Update shared library cache
    ldconfig
%environment
    export LC_ALL=en_US.UTF-8
    export LANG=en_US.UTF-8
    export PYTHONUNBUFFERED=1
    export DATA_DIR=/data
    # Add critical environment variables for X11
    export QT_X11_NO_MITSHM=1
    export XDG_RUNTIME_DIR=/tmp/runtime-user
    # XAUTHORITY will point to the file bound from the host
    export XAUTHORITY=${XAUTHORITY:-/tmp/guest_xauth} 
    # Explicitly set QPA platform to xcb
    export QT_QPA_PLATFORM=xcb
    # Remove explicit Qt plugin path overrides to let PyQt6 use its own.
    # export QT_PLUGIN_PATH=/usr/lib/x86_64-linux-gnu/qt6/plugins
    # export QT_QPA_PLATFORM_PLUGIN_PATH=/usr/lib/x86_64-linux-gnu/qt6/plugins/platforms
    # Enable Qt plugin debugging
    export QT_DEBUG_PLUGINS=1

%runscript
    # Ensure critical environment variables are set for this script's execution
    # These should ideally be inherited from %environment or passed by apptainer --env,
    # but we set them explicitly here for maximum robustness within the runscript's shell.

    # DISPLAY is passed by apptainer run --env DISPLAY="$DISPLAY"
    export DISPLAY="${DISPLAY}"
    
    # XAUTHORITY is passed by apptainer run --env XAUTHORITY="/tmp/guest_xauth"
    # and bound from the host.
    export XAUTHORITY="${XAUTHORITY:-/tmp/guest_xauth}"
    
    export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-xcb}"
    export QT_DEBUG_PLUGINS="${QT_DEBUG_PLUGINS:-1}"
    export QT_X11_NO_MITSHM="${QT_X11_NO_MITSHM:-1}"
    
    # Set XDG_RUNTIME_DIR *before* using it
    export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/tmp/runtime-$(id -u)}"
    mkdir -p "${XDG_RUNTIME_DIR}"
    chmod 700 "${XDG_RUNTIME_DIR}"

    echo "--- Apptainer Runscript Diagnostics ---"
    echo "User: $(whoami)"
    echo "Effective PATH=${PATH}"
    
    echo "DISPLAY=${DISPLAY}"
    
    echo -n "XAUTHORITY (env var value): "
    env | grep "^XAUTHORITY=" || echo "XAUTHORITY not in env"
    
    if [ -n "${XAUTHORITY}" ] && [ -f "${XAUTHORITY}" ]; then
        echo "Xauthority file exists at ${XAUTHORITY}. Permissions:"
        ls -l "${XAUTHORITY}"
    elif [ -n "${XAUTHORITY}" ]; then
        echo "Xauthority file NOT FOUND at path: ${XAUTHORITY}"
    else
        echo "XAUTHORITY environment variable is not set or empty."
    fi
    
    echo "QT_QPA_PLATFORM=${QT_QPA_PLATFORM}"
    echo "QT_DEBUG_PLUGINS=${QT_DEBUG_PLUGINS}"
    echo "LD_LIBRARY_PATH=${LD_LIBRARY_PATH}"
    echo "XDG_RUNTIME_DIR=${XDG_RUNTIME_DIR}"

    echo "Checking for xdpyinfo..."
    type xdpyinfo || echo "type: xdpyinfo not found"
    ls -l /usr/bin/xdpyinfo || echo "/usr/bin/xdpyinfo not found"
    
    echo "Attempting to run xdpyinfo..."
    xdpyinfo || echo "xdpyinfo failed"
    
    echo "Attempting to run xeyes (close manually if it appears)..."
    # Run xeyes in background and timeout, as it blocks
    (xeyes & PID=$! ; sleep 5 ; kill $PID >/dev/null 2>&1) || echo "xeyes command failed or timed out"
    echo "--- End Diagnostics ---"

    echo "Starting ResearchGuide Application..."
    cd /app && python main.py "\$@"

%startscript
    cd /app && python main.py

%help
    ResearchGuide Application Container
    
    This container runs the ResearchGuide application using
    a pure Apptainer definition (no Docker dependency).
    
    Usage:
      Regular run:
        apptainer run --bind ./apptainer_data:/data researchguide.sif
        
      For custom data directory:
        apptainer run --bind /custom/path:/data researchguide.sif
EOF

echo "✓ Apptainer definition file created at ${DEF_FILE}"

# Build the Apptainer container with better error handling
echo "Building Apptainer container... (this may take a few minutes)"

# First try with standard build
if apptainer build "${SIF_FILE}" "${DEF_FILE}" 2>/tmp/apptainer_error.log; then
    echo "✓ Apptainer container built successfully at ${SIF_FILE}"
else
    # If standard build fails, check if it's a permissions issue
    if grep -q "FATAL:.*fakeroot\|permission denied\|Operation not permitted" /tmp/apptainer_error.log; then
        echo "Standard build failed due to permissions. Trying with sudo..."
        
        # Check if sudo is available
        if command -v sudo &> /dev/null; then
            if sudo apptainer build "${SIF_FILE}" "${DEF_FILE}"; then
                echo "✓ Apptainer container built successfully with sudo at ${SIF_FILE}"
                # Fix permissions for the generated files
                sudo chown -R $(id -u):$(id -g) "${SIF_FILE}" "${DATA_DIR}"
            else
                echo "ERROR: Build with sudo failed."
                echo "Please manually run one of the following commands:"
                echo "  sudo apptainer build ${SIF_FILE} ${DEF_FILE}"
                echo "  sudo -E apptainer build --sandbox ${CONTAINERS_DIR}/sandbox ${DEF_FILE}"
                echo "  apptainer build --remote ${SIF_FILE} ${DEF_FILE} (if remote builder is configured)"
                exit 1
            fi
        else
            echo "ERROR: Build failed and sudo is not available."
            echo "To fix the fakeroot issue, you can:"
            echo "1. Run as a user with appropriate permissions"
            echo "2. Have an administrator configure fakeroot for your user:"
            echo "   sudo usermod --add-subuids 100000-165535 \$(whoami)"
            echo "   sudo usermod --add-subgids 100000-165535 \$(whoami)"
            echo "3. Try building as root directly"
            echo "4. Use the remote builder if available:"
            echo "   apptainer build --remote ${SIF_FILE} ${DEF_FILE}"
            exit 1
        fi
    else
        # Some other error occurred
        echo "ERROR: Build failed for unknown reason."
        echo "Check the error log at /tmp/apptainer_error.log"
        cat /tmp/apptainer_error.log
        exit 1
    fi
fi

# Create a simple wrapper script to run the container in makros directory
WRAPPER_SCRIPT="${SCRIPT_DIR}/RunPrebuiltApptainer.sh"
cat > "${WRAPPER_SCRIPT}" << EOF
#!/bin/bash

# Simple script to run the ResearchGuide Apptainer container
# Usage: ./RunPrebuiltApptainer.sh [app arguments]

SCRIPT_DIR="\$(cd "\$(dirname "\${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="\$(dirname "\${SCRIPT_DIR}")"
SIF_FILE="\${PROJECT_DIR}/containers/researchguide.sif"
DATA_DIR="\${PROJECT_DIR}/containers/apptainer_data"

# Ensure XAUTHORITY is set and points to a valid file on the host
# If running with sudo, $HOME might be /root. Try to find original user's home.
CURRENT_USER_HOME="\$HOME"
if [ -n "\$SUDO_USER" ]; then
    USER_HOME_TEMP=\$(getent passwd "\$SUDO_USER" | cut -d: -f6)
    if [ -d "\$USER_HOME_TEMP" ]; then
        CURRENT_USER_HOME="\$USER_HOME_TEMP"
    fi
fi
export HOST_XAUTHORITY_FILE="\${XAUTHORITY:-\$CURRENT_USER_HOME/.Xauthority}"

if [ ! -f "\$HOST_XAUTHORITY_FILE" ]; then
    echo "Warning: Host XAUTHORITY file (\$HOST_XAUTHORITY_FILE) not found. GUI might not work."
    echo "Please ensure XAUTHORITY is set correctly in your host environment or that \$CURRENT_USER_HOME/.Xauthority exists."
fi

echo "Starting ResearchGuide Application..."
echo "Host DISPLAY: \$DISPLAY"
echo "Host XAUTHORITY path to be bound: \$HOST_XAUTHORITY_FILE"
echo "Binding \$HOST_XAUTHORITY_FILE to /tmp/guest_xauth in container."

# Run the container
apptainer run \\
  --env DISPLAY="\$DISPLAY" \\
  --env XAUTHORITY="/tmp/guest_xauth" \\
  --bind /tmp/.X11-unix:/tmp/.X11-unix \\
  --bind "\$HOST_XAUTHORITY_FILE":/tmp/guest_xauth:ro \\
  --bind "\${DATA_DIR}":/data \\
  "\${SIF_FILE}" "\$@"
EOF
chmod +x "${WRAPPER_SCRIPT}"

echo "✓ Created wrapper script: ${WRAPPER_SCRIPT}"

echo ""
echo "===== Build Complete ====="
echo "The container has been built with all dependencies included."
echo ""
echo "To run ResearchGuide simply use:"
echo "  ${WRAPPER_SCRIPT}"
echo ""
echo "Persistent data is stored in: ${DATA_DIR}"
echo ""
