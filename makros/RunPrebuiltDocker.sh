#!/bin/bash

# RunPrebuiltDockerImage.sh - A script to load and run a pre-built Docker image for ResearchGuide

IMAGE_NAME="researchguide-app:latest"
IMAGE_TARBALL="./researchguide-app.tar" # Assumes tarball is in the current directory
CONTAINER_NAME="researchguide_prebuilt_container"

echo "---------------------------------------------------------------------"
echo "ResearchGuide Pre-built Docker Image Run Script"
echo "Using image name: $IMAGE_NAME (from $IMAGE_TARBALL)"
echo "Container name: $CONTAINER_NAME"
echo "---------------------------------------------------------------------"
echo ""
echo "This script will attempt to load $IMAGE_TARBALL and run the container."
echo "IMPORTANT: This script should be run from your project's root directory,"
echo "           the same directory containing your application code and $IMAGE_TARBALL."
echo ""

echo "IMPORTANT PRE-REQUISITE FOR GUI APPLICATIONS:"
echo "If your application has a GUI, ensure you have allowed X11"
echo "connections from Docker by running this command in your host terminal:"
echo "  xhost +local:docker"
echo "This script will attempt to run it for you."
echo ""

echo "PERMISSION NOTE:"
echo "If you encounter permission errors with Docker commands (e.g., 'Permission denied'),"
echo "you might need to:"
echo "1. Add your user to the 'docker' group: "
echo "   sudo usermod -aG docker \${USER}"
echo "   (You'll need to log out and log back in or start a new terminal session for this to take effect)"
echo "2. Or, ensure this script is run with 'sudo' if Docker commands require it."
echo ""

# Attempt to allow X11 connections for GUI applications
echo "Attempting to allow X11 connections from Docker (xhost +local:docker)..."
if xhost +local:docker; then
    echo "Successfully executed 'xhost +local:docker'."
else
    echo "Warning: 'xhost +local:docker' command may have failed."
    echo "If you are running a GUI application and encounter display issues,"
    echo "please ensure X11 connections are allowed manually from your host terminal."
fi
echo ""

# Check if the image tarball exists
if [ ! -f "$IMAGE_TARBALL" ]; then
    echo "ERROR: Image tarball '$IMAGE_TARBALL' not found in the current directory."
    echo "Please ensure the tarball is present and you are in the correct directory."
    exit 1
fi

echo "Loading image from $IMAGE_TARBALL..."
if sudo docker load -i "$IMAGE_TARBALL"; then
    echo "Image loaded successfully from $IMAGE_TARBALL."
else
    echo "ERROR: Failed to load image from $IMAGE_TARBALL."
    echo "Please check if the tarball is valid and Docker is running."
    exit 1
fi
echo ""

echo "Attempting to run the Docker container: $IMAGE_NAME"
echo "Container will be named: $CONTAINER_NAME"
echo "Application code from the current directory ($(pwd)) will be mounted to /app in the container."
echo ""

# Run the container
# These parameters mirror a typical docker-compose setup for a GUI app
sudo docker run --rm -it \
    --name "$CONTAINER_NAME" \
    -v "$(pwd)":/app \
    -v /tmp/.X11-unix:/tmp/.X11-unix \
    -e DISPLAY=$DISPLAY \
    --network="host" \
    "$IMAGE_NAME"

# Check the exit status of docker run
if [ $? -eq 0 ]; then
  echo ""
  echo "---------------------------------------------------------------------"
  echo "Container exited."
  echo "---------------------------------------------------------------------"
else
  echo ""
  echo "---------------------------------------------------------------------"
  echo "ERROR: The docker run command failed or the container exited with an error."
  echo "---------------------------------------------------------------------"
  echo "Please check the output above for specific error messages."
fi

echo ""
echo "REMINDER FOR GUI APPLICATIONS:"
echo "When you are finished, it's good practice to restrict X11 connections again for security:"
echo "  xhost -local:docker"
echo ""
echo "---------------------------------------------------------------------"