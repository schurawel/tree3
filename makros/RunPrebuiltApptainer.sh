#!/bin/bash

# Simple script to run the ResearchGuide Apptainer container
# Usage: ./RunPrebuiltApptainer.sh [app arguments]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "${SCRIPT_DIR}")"
SIF_FILE="${PROJECT_DIR}/containers/researchguide.sif"
DATA_DIR="${PROJECT_DIR}/containers/apptainer_data"

# Ensure XAUTHORITY is set and points to a valid file on the host
# If running with sudo, /root might be /root. Try to find original user's home.
CURRENT_USER_HOME="$HOME"
if [ -n "$SUDO_USER" ]; then
    USER_HOME_TEMP=$(getent passwd "$SUDO_USER" | cut -d: -f6)
    if [ -d "$USER_HOME_TEMP" ]; then
        CURRENT_USER_HOME="$USER_HOME_TEMP"
    fi
fi
export HOST_XAUTHORITY_FILE="${XAUTHORITY:-$CURRENT_USER_HOME/.Xauthority}"

if [ ! -f "$HOST_XAUTHORITY_FILE" ]; then
    echo "Warning: Host XAUTHORITY file ($HOST_XAUTHORITY_FILE) not found. GUI might not work."
    echo "Please ensure XAUTHORITY is set correctly in your host environment or that $CURRENT_USER_HOME/.Xauthority exists."
fi

echo "Starting ResearchGuide Application..."
echo "Host DISPLAY: $DISPLAY"
echo "Host XAUTHORITY path to be bound: $HOST_XAUTHORITY_FILE"
echo "Binding $HOST_XAUTHORITY_FILE to /tmp/guest_xauth in container."

# Run the container
apptainer run \
  --env DISPLAY="$DISPLAY" \
  --env XAUTHORITY="/tmp/guest_xauth" \
  --bind /tmp/.X11-unix:/tmp/.X11-unix \
  --bind "$HOST_XAUTHORITY_FILE":/tmp/guest_xauth:ro \
  --bind "${DATA_DIR}":/data \
  "${SIF_FILE}" "$@"
