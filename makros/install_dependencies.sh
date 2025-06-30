#!/bin/bash

# ResearchGuide Dependencies Installer Script
# ==========================================
# This script installs all necessary dependencies for the ResearchGuide application,
# including system libraries and Python packages.
#
# It requires sudo privileges to install system packages.
#
# Run with:
#   bash install_dependencies.sh
#
# Author: Jason A. Schurawel

set -e  # Exit immediately if a command exits with non-zero status

# Define colors for output
GREEN="\033[0;32m"
RED="\033[0;31m"
YELLOW="\033[0;33m"
NC="\033[0m" # No Color

echo -e "${GREEN}===== ResearchGuide Dependencies Installer =====${NC}"

# Check if running with sudo/root
if [ "$(id -u)" -ne 0 ]; then
    echo -e "${YELLOW}This script needs to install system packages and requires sudo privileges.${NC}"
    echo -e "${YELLOW}Please run this script as root or with sudo.${NC}"
    exit 1
fi

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Function to install apt packages with better error handling
install_apt_packages() {
    local package_list=("$@")
    
    echo -e "${GREEN}Installing ${#package_list[@]} apt packages...${NC}"
    
    # Try to install all packages at once first
    if apt-get install -y "${package_list[@]}" >/dev/null 2>&1; then
        echo -e "${GREEN}✓ All packages installed successfully${NC}"
        return 0
    else
        echo -e "${YELLOW}Some packages failed to install. Trying individual installations...${NC}"
        
        # If that fails, try installing each package individually
        local failed_packages=()
        for package in "${package_list[@]}"; do
            echo -n "Installing $package... "
            if apt-get install -y "$package" >/dev/null 2>&1; then
                echo -e "${GREEN}OK${NC}"
            else
                echo -e "${RED}FAILED${NC}"
                failed_packages+=("$package")
            fi
        done
        
        if [ ${#failed_packages[@]} -gt 0 ]; then
            echo -e "${RED}The following packages could not be installed:${NC}"
            for pkg in "${failed_packages[@]}"; do
                echo " - $pkg"
            done
            return 1
        fi
    fi
}

echo -e "${GREEN}Updating package lists...${NC}"
apt-get update

# First install critical X11 libraries
echo -e "${GREEN}Installing X11 and XCB libraries...${NC}"
X11_LIBS=(
    libx11-dev
    libxext-dev
    libxrender-dev
    libxrandr-dev
    libxfixes-dev
    libxcomposite-dev
    libxcursor-dev
    libxdamage-dev
    libxkbcommon-dev
    libxkbcommon-x11-dev
    libx11-xcb-dev
    libxcb1-dev
    libxcb-keysyms1-dev
    libxcb-image0-dev
    libxcb-shm0-dev
    libxcb-icccm4-dev
    libxcb-xfixes0-dev
    libxcb-shape0-dev
    libxcb-randr0-dev
    libxcb-render-util0-dev
    libxcb-glx0-dev
    libxcb-xinerama0-dev
    libxcb-dri3-dev
    libxcb-present-dev
    libxcb-xkb-dev
    libxcb-xinput-dev
    libxcb-cursor0
    libxcb-xkb1
    libxkbcommon-x11-0
    libxcb-xinerama0
    libxcb-xinput0
    libglu1-mesa-dev
    libx11-xcb1
    libxcb-dri3-0
    libxcb-present0
    libx11-6
)
install_apt_packages "${X11_LIBS[@]}"

# Then install Python, build tools and Qt dependencies
echo -e "${GREEN}Installing Python, Qt and build tools...${NC}"
BUILD_TOOLS=(
    python3
    python3-pip
    python3-dev
    xauth
    build-essential
    cmake
    git
    libgl1-mesa-glx
    qt6-base-dev
)
install_apt_packages "${BUILD_TOOLS[@]}"

# Then install additional libraries
echo -e "${GREEN}Installing additional libraries...${NC}"
ADDITIONAL_LIBS=(
    apt-utils
    libxcb-sync1
    libxcb-render-util0
    libxcb-util1
    libnss3
    libnspr4
    libasound2
    libasound2-plugins
    libxslt1.1
    libxcomposite1
    libxdamage1
    libxtst6
    libxrandr2
    libegl1
    libxfixes3
    libxrender1
    libxi6
    libgbm1
    libxkbfile1
    libxkbcommon0
    libpulse0
    libdbus-1-3
    libfontconfig1
    libfreetype6
    libxext6
    libharfbuzz0b
    libicu70
    libjpeg-turbo8
    libpng16-16
    libxml2
    libsqlite3-0
    libevent-2.1-7
    fontconfig
)
install_apt_packages "${ADDITIONAL_LIBS[@]}"

# Install fonts
echo -e "${GREEN}Installing fonts...${NC}"
FONTS=(
    fonts-noto-core
    fonts-noto-color-emoji
    fonts-freefont-ttf
)
install_apt_packages "${FONTS[@]}"

# Install multimedia libraries
echo -e "${GREEN}Installing multimedia libraries...${NC}"
MULTIMEDIA_LIBS=(
    libavcodec58
    libavformat58
    libavutil56
    libvpx7
    libopus0
    libwebp7
    libopenjp2-7
)
install_apt_packages "${MULTIMEDIA_LIBS[@]}"

# Install X11 apps and tools
echo -e "${GREEN}Installing X11 apps and tools...${NC}"
X11_APPS=(
    x11-apps
    mesa-utils
    ca-certificates
)
install_apt_packages "${X11_APPS[@]}"

# Create Python symlink if needed
if [ ! -x "/usr/bin/python" ]; then
    echo -e "${GREEN}Creating python symlink...${NC}"
    if [ -x "/usr/bin/python3" ]; then
        ln -sf /usr/bin/python3 /usr/bin/python
        echo -e "${GREEN}✓ Created symlink from /usr/bin/python3 to /usr/bin/python${NC}"
    else
        echo -e "${RED}Python3 not found at /usr/bin/python3!${NC}"
    fi
fi

# Install Python dependencies
echo -e "${GREEN}Installing Python dependencies...${NC}"
if [ -f "${SCRIPT_DIR}/requirements.txt" ]; then
    python3 -m pip install --upgrade pip setuptools wheel

    # Install PyQt6 components separately with better error handling
    echo -e "${GREEN}Installing PyQt6 components...${NC}"
    QT_PACKAGES=("PyQt6" "PyQt6-Qt6" "PyQt6-WebEngine" "PyQt6-sip")
    for package in "${QT_PACKAGES[@]}"; do
        echo -n "Installing $package... "
        if python3 -m pip install "$package"; then
            echo -e "${GREEN}OK${NC}"
        else
            echo -e "${YELLOW}Failed but continuing${NC}"
        fi
    done

    # Install remaining requirements
    echo -e "${GREEN}Installing other Python dependencies...${NC}"
    if python3 -m pip install -r "${SCRIPT_DIR}/requirements.txt"; then
        echo -e "${GREEN}✓ Python dependencies installed successfully${NC}"
    else
        echo -e "${RED}Some Python dependencies failed to install${NC}"
    fi
else
    echo -e "${RED}requirements.txt not found at ${SCRIPT_DIR}/requirements.txt${NC}"
fi

# Final system setup
ldconfig
echo -e "${GREEN}✓ System library cache updated${NC}"

echo -e "${GREEN}===== Installation Complete =====${NC}"
echo -e "${GREEN}You can now run the ResearchGuide application using:${NC}"
echo -e "${YELLOW}bash run_python_app.sh${NC}"
