#!/bin/bash

# BuildDocker.sh - A script to build and run the Docker container for ResearchGuide

IMAGE_NAME="researchguide-app:latest"
IMAGE_TARBALL="./researchguide-app.tar" # Store tarball in the current directory

echo "---------------------------------------------------------------------"
echo "ResearchGuide Docker Build & Run Script"
echo "Using image name: $IMAGE_NAME"
echo "Image tarball: $IMAGE_TARBALL"
echo "---------------------------------------------------------------------"
echo ""
echo "This script will attempt to build and run the Docker container."
echo "It will also save the built image to $IMAGE_TARBALL for faster reuse."
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
echo "2. Or, run 'docker-compose' commands with 'sudo', e.g., 'sudo docker-compose up --build'."
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

# Optionally load image from tarball if it exists
if [ -f "$IMAGE_TARBALL" ]; then
    echo "Found local image archive: $IMAGE_TARBALL"
    read -p "Do you want to load this image before building? (This can speed up the build if no source files changed) (y/N): " load_image_choice
    if [[ "$load_image_choice" =~ ^[Yy]$ ]]; then
        echo "Loading image from $IMAGE_TARBALL..."
        if sudo docker load -i "$IMAGE_TARBALL"; then # Added sudo, adjust if not needed
            echo "Image loaded successfully from $IMAGE_TARBALL."
        else
            echo "Failed to load image from $IMAGE_TARBALL. Proceeding with full build if necessary."
        fi
    fi
    echo ""
fi

# Ask the user if they want to run in detached mode
read -p "Do you want to run in detached mode (-d)? (This will run the container in the background) (y/N): " detached_mode

echo ""
echo "Building and starting the Docker container(s) via docker-compose..."
echo "This might take a while, especially on the first run or if dependencies have changed."
echo ""

DOCKER_COMPOSE_CMD="docker-compose up --build"
if [[ "$detached_mode" =~ ^[Yy]$ ]]; then
  echo "Executing: sudo $DOCKER_COMPOSE_CMD -d" # Added sudo
  sudo $DOCKER_COMPOSE_CMD -d
else
  echo "Executing: sudo $DOCKER_COMPOSE_CMD" # Added sudo
  sudo $DOCKER_COMPOSE_CMD
fi

# Check the exit status of docker-compose
if [ $? -eq 0 ]; then
  echo ""
  echo "---------------------------------------------------------------------"
  echo "Docker command executed successfully."
  echo "---------------------------------------------------------------------"

  echo "Attempting to save image $IMAGE_NAME to $IMAGE_TARBALL..."
  if sudo docker save "$IMAGE_NAME" -o "$IMAGE_TARBALL"; then # Added sudo
      echo "Image $IMAGE_NAME successfully saved to $IMAGE_TARBALL"
  else
      echo "ERROR: Failed to save image $IMAGE_NAME to $IMAGE_TARBALL."
      echo "The image might not have been built with the tag '$IMAGE_NAME',"
      echo "or another error occurred. Check 'docker images' to see available images."
  fi
  echo ""

  if [[ "$detached_mode" =~ ^[Yy]$ ]]; then
    echo "The application should now be running in the background (detached mode)."
    echo "To view logs, you can use: sudo docker-compose logs -f"
    echo "To stop the container(s), use: sudo docker-compose down"
  else
    echo "The application should be running in this terminal."
    echo "Press Ctrl+C in this terminal to stop the container(s)."
    echo "Alternatively, from another terminal, you can use: sudo docker-compose down"
  fi
else
  echo ""
  echo "---------------------------------------------------------------------"
  echo "ERROR: The docker-compose command failed."
  echo "---------------------------------------------------------------------"
  echo "Please check the output above for specific error messages."
  echo "Common troubleshooting steps:"
  echo "  - Ensure the Docker daemon is running on your system."
  echo "  - Verify your Dockerfile and docker-compose.yml for syntax errors or misconfigurations."
  echo "  - Check for permission issues (see 'PERMISSION NOTE' above)."
  echo "  - Ensure your docker-compose.yml specifies 'image: $IMAGE_NAME' for the service."
  echo ""
fi

echo ""
echo "REMINDER FOR GUI APPLICATIONS:"
echo "When you are finished and have stopped the container(s),"
echo "it's good practice to restrict X11 connections again for security:"
echo "  xhost -local:docker"
echo ""
echo "---------------------------------------------------------------------"