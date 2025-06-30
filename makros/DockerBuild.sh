#!/bin/bash

# DockerBuild.sh - Builds Docker containers for ResearchGuide
# Author: Based on the ResearchGuide application by Jason A. Schurawel

set -e  # Exit immediately if a command exits with a non-zero status

# Define variables
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "${SCRIPT_DIR}")"
CONTAINERS_DIR="${PROJECT_DIR}/containers"
DOCKER_DATA_DIR="${CONTAINERS_DIR}/docker_data"

echo "===== ResearchGuide Docker Builder ====="

# Create necessary directories
mkdir -p "${CONTAINERS_DIR}"
mkdir -p "${DOCKER_DATA_DIR}"

echo "✓ Containers directory: ${CONTAINERS_DIR}"
echo "✓ Docker data directory: ${DOCKER_DATA_DIR}"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed. Please install Docker first."
    exit 1
fi

echo "✓ Docker detected: $(docker --version)"

# Build the Docker image
echo "Building Docker image..."
docker-compose build

# Create wrapper scripts
WRAPPER_DOCKER="${CONTAINERS_DIR}/run_researchguide_docker.sh"
cat > "${WRAPPER_DOCKER}" << EOF
#!/bin/bash

# Run the ResearchGuide Docker container
docker-compose up
EOF
chmod +x "${WRAPPER_DOCKER}"

# Create a symlink in the project root
ln -sf "${WRAPPER_DOCKER}" "${PROJECT_DIR}/run_docker.sh"

echo "✓ Created wrapper script: ${WRAPPER_DOCKER}"
echo "✓ Created symlink in project root for convenience"

echo ""
echo "===== Build Complete ====="
echo "The Docker container has been built."
echo ""
echo "To run ResearchGuide with Docker:"
echo "  ${PROJECT_DIR}/run_docker.sh"
echo ""
echo "Or use standard Docker Compose commands:"
echo "  docker-compose up"
echo ""
echo "Persistent data is stored in: ${DOCKER_DATA_DIR}"
echo ""
