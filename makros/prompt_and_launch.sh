#!/bin/bash

# prompt_and_launch.sh - A helper script to prompt the user and launch the application

# The first argument should be the path to the launcher script
LAUNCHER_PATH="$1"

if [ ! -f "$LAUNCHER_PATH" ]; then
    echo "ERROR: Launcher script '$LAUNCHER_PATH' not found."
    exit 1
fi

if [ ! -x "$LAUNCHER_PATH" ]; then
    echo "ERROR: Launcher script '$LAUNCHER_PATH' is not executable."
    echo "Please run: chmod +x \"$LAUNCHER_PATH\"" # Added quotes for safety
    exit 1
fi

# Determine the original user
# Use logname as a primary method, fallback to whoami if logname is not available or empty
ORIGINAL_USER=$(logname 2>/dev/null)
if [ -z "$ORIGINAL_USER" ]; then
    ORIGINAL_USER=$(whoami)
fi

if [ -z "$ORIGINAL_USER" ] || [ "$ORIGINAL_USER" = "root" ]; then
    echo "ERROR: Could not determine a non-root original user to run the application as."
    echo "       (logname: '$(logname 2>/dev/null)', whoami: '$(whoami)')"
    exit 1
fi
echo "INFO: Determined original user as: $ORIGINAL_USER"

# Prompt the user
read -r -p "Do you want to launch the application now? (y/N): " response
if [[ "$response" =~ ^[Yy]$ ]]; then
    echo "Launching application as user $ORIGINAL_USER..."
    # Execute LaunchCompiled.sh as the original user, as suggested by its error message.
    # sudo is still used here to allow LaunchCompiled.sh to potentially elevate privileges
    # for specific tasks if it's designed to do so (e.g., its own internal sudo calls).
    # However, the primary execution context for LaunchCompiled.sh will be $ORIGINAL_USER.
    sudo -u "$ORIGINAL_USER" "$LAUNCHER_PATH"
else
    echo "Application not launched. You can run it later with 'make run-only'."
fi

exit 0
