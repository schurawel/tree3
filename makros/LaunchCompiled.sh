#!/bin/bash

# LaunchCompiled.sh - A script to launch the compiled Python application

# Determine the absolute path to the directory where this script resides
_SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

APP_NAME="ResearchGuideApp" # Name of the output executable (must match CompileApplication.sh)
# _ABS_OUTPUT_DIR is one level up from this script's directory, then into 'dist'
# This makes it robust to the CWD the script is called from.
_ABS_OUTPUT_DIR="$_SCRIPT_DIR/../dist"
# Normalize the path (e.g., /path/to/project/makros/../dist becomes /path/to/project/dist)
_ABS_OUTPUT_DIR="$(cd "$_ABS_OUTPUT_DIR" && pwd)"

_ABS_EXECUTABLE_PATH="$_ABS_OUTPUT_DIR/$APP_NAME/$APP_NAME" 

echo "---------------------------------------------------------------------"
echo "ResearchGuide Application Launcher (--onedir mode)"
echo "---------------------------------------------------------------------"
echo "DEBUG_LAUNCHER: Script's own directory: $_SCRIPT_DIR"
echo "DEBUG_LAUNCHER: Calculated absolute OUTPUT_DIR: $_ABS_OUTPUT_DIR"
echo "DEBUG_LAUNCHER: Calculated absolute EXECUTABLE_PATH: $_ABS_EXECUTABLE_PATH"
echo "DEBUG_LAUNCHER: Current working directory at script start: $(pwd)"
echo ""

# Check and set XDG_RUNTIME_DIR if not set
if [ -z "$XDG_RUNTIME_DIR" ]; then
    # Attempt to set a common default for XDG_RUNTIME_DIR
    CANDIDATE_XDG_RUNTIME_DIR="/run/user/$(id -u)"
    if [ -d "$CANDIDATE_XDG_RUNTIME_DIR" ] && [ -w "$CANDIDATE_XDG_RUNTIME_DIR" ]; then
        export XDG_RUNTIME_DIR="$CANDIDATE_XDG_RUNTIME_DIR"
        echo "INFO: XDG_RUNTIME_DIR was not set. Temporarily set to $XDG_RUNTIME_DIR"
    else
        # Fallback if the standard path is not writable or doesn't exist
        TEMP_XDG_DIR=$(mktemp -d -t xdg_runtime_XXXXXX)
        export XDG_RUNTIME_DIR="$TEMP_XDG_DIR"
        echo "WARNING: XDG_RUNTIME_DIR was not set and standard path '$CANDIDATE_XDG_RUNTIME_DIR' is not usable."
        echo "INFO: Temporarily set XDG_RUNTIME_DIR to $XDG_RUNTIME_DIR. This directory will be removed on script exit."
        # Clean up the temporary directory on exit
        trap 'rm -rf "$TEMP_XDG_DIR" >/dev/null 2>&1' EXIT
    fi
fi
echo ""

APP_LAUNCH_ARGS=""
# Check if running as root
if [ "$(id -u)" -eq 0 ]; then
   echo "WARNING: Script is running as root. The xhost command will be executed with root privileges,"
   echo "but the application will be launched as a normal user for security reasons."
   
   # DEBUG: Print SUDO_USER and USER
   echo "DEBUG_LAUNCHER: SUDO_USER='${SUDO_USER}', USER='${USER}'"

   # Get the user who executed sudo (the actual user)
   ACTUAL_USER=${SUDO_USER:-$USER}
   if [ -z "$ACTUAL_USER" ] || [ "$ACTUAL_USER" = "root" ]; then
       echo "ERROR: Cannot determine the original user. Please run this script with sudo,"
       echo "or specify the normal user with sudo -u username \"$0\"" # Use $0 for script name
       exit 1
   fi
   
   # Run xhost as root (which we are now)
   echo "INFO: Running xhost +local:docker as root..."
   xhost +local:docker
   
   # Fix permissions for the entire dist directory
   if [ -d "$_ABS_OUTPUT_DIR" ]; then # Use absolute path
       echo "Fixing permissions on $_ABS_OUTPUT_DIR to allow user $ACTUAL_USER to access and modify..."
       chown -R "$ACTUAL_USER:$(id -gn $ACTUAL_USER)" "$_ABS_OUTPUT_DIR"
       chmod -R u+rw "$_ABS_OUTPUT_DIR"
   fi
   
   # Create a user-specific data directory for runtime files if it doesn't exist
   USER_DATA_DIR="/home/$ACTUAL_USER/.local/share/ResearchGuideApp"
   mkdir -p "$USER_DATA_DIR"
   chown -R "$ACTUAL_USER:$(id -gn $ACTUAL_USER)" "$USER_DATA_DIR"
   chmod -R u+rw "$USER_DATA_DIR"
   
   # Make sure the executable has proper permissions
   echo "INFO: Ensuring executable permissions..."
   if [ -f "$_ABS_EXECUTABLE_PATH" ]; then # Use absolute path
       chmod +x "$_ABS_EXECUTABLE_PATH"
       chown "$ACTUAL_USER:$(id -gn $ACTUAL_USER)" "$_ABS_EXECUTABLE_PATH"
   fi
   
   # Set environment variable for the app to use the user data directory
   export RESEARCH_GUIDE_DATA_DIR="$USER_DATA_DIR"
   
   # Execute the application directly as the user
   echo "INFO: Launching application as user $ACTUAL_USER..."
   if [ -f "$_ABS_EXECUTABLE_PATH" ] && [ -x "$_ABS_EXECUTABLE_PATH" ]; then # Use absolute path
       cd "$_ABS_OUTPUT_DIR/$APP_NAME" || exit 1 # cd to absolute path
       echo "Changing to $_ABS_OUTPUT_DIR/$APP_NAME and running as user $ACTUAL_USER"
       # Pass the data directory environment variable to the user's process
       exec sudo -u "$ACTUAL_USER" env "RESEARCH_GUIDE_DATA_DIR=$USER_DATA_DIR" ./"$APP_NAME" $APP_LAUNCH_ARGS
   else
       echo "ERROR: Application not found or not executable at $_ABS_EXECUTABLE_PATH" # Use absolute path
       exit 1
   fi
   
   exit $?
else # Not running as root
   # Create a user-specific data directory for runtime files if it doesn't exist
   USER_DATA_DIR="$HOME/.local/share/ResearchGuideApp"
   mkdir -p "$USER_DATA_DIR"
   export RESEARCH_GUIDE_DATA_DIR="$USER_DATA_DIR"

   # --- Symlink Workaround Setup (Non-Root Path) --- REMOVED ---
   # --- End Symlink Workaround ---
   
   # Normal user handling for --no-sandbox
   if [ -n "$SUDO_USER" ]; then
      # We're being run by the above code, no need for xhost command
      echo "INFO: Running as normal user after handoff from root."
   else
      # Direct normal user execution, try xhost with sudo
      echo "INFO: Attempting to run xhost +local:docker with sudo..."
      if sudo -n xhost +local:docker 2>/dev/null; then
         echo "Successfully ran xhost with sudo."
      else
         echo "WARNING: Could not run 'xhost +local:docker' with sudo. X11 forwarding might not work."
         echo "You may need to run this command manually or give this user passwordless sudo for xhost."
      fi
   fi
fi

# Check if the executable exists (this block is reached by non-root execution path)
echo "DEBUG_LAUNCHER: Final check. CWD: $(pwd), EXECUTABLE_PATH: $_ABS_EXECUTABLE_PATH"
if [ -f "$_ABS_EXECUTABLE_PATH" ]; then # Use absolute path
    # Check if the file is executable
    if [ -x "$_ABS_EXECUTABLE_PATH" ]; then # Use absolute path
        echo "Found executable at: $_ABS_EXECUTABLE_PATH"
        # The PYTHONPATH set here refers to the original project structure.
        # Project root for PYTHONPATH, derived from script's location
        _PROJECT_ROOT="$(cd "$_SCRIPT_DIR/.." && pwd)"
        echo "Setting PYTHONPATH to $_PROJECT_ROOT/researchguide:$_PROJECT_ROOT for the application's environment."
        export PYTHONPATH="$_PROJECT_ROOT/researchguide:$_PROJECT_ROOT"
        echo "Attempting to launch the application..."
        echo ""
        # Change directory to where the executable and its dependencies are
        cd "$_ABS_OUTPUT_DIR/$APP_NAME" || exit 1 # cd to absolute path
        # xhost command is now handled above based on user privileges
        ./"$APP_NAME" $APP_LAUNCH_ARGS # Execute the application with arguments
        LAUNCH_EXIT_CODE=$?
        echo ""
        echo "---------------------------------------------------------------------"
        if [ $LAUNCH_EXIT_CODE -eq 0 ]; then
            echo "Application exited normally."
        else
            echo "Application exited with code: $LAUNCH_EXIT_CODE"
        fi
        echo "---------------------------------------------------------------------"
        # Optionally, navigate back to the original directory
        # cd - > /dev/null
    else
        echo "ERROR: Application '$_ABS_EXECUTABLE_PATH' found but is not executable." # Use absolute path
        echo "Please check file permissions or try recompiling."
        echo "You might need to run: chmod +x \"$_ABS_EXECUTABLE_PATH\"" # Use absolute path
        exit 1
    fi
else
    echo "ERROR: Compiled application '$_ABS_EXECUTABLE_PATH' not found." # Use absolute path
    echo "Please ensure you have compiled the application using CompileApplication.sh"
    echo "The executable should be located at: $_ABS_EXECUTABLE_PATH" # Use absolute path
    echo "Note: For --onedir mode, this path is $_ABS_OUTPUT_DIR/$APP_NAME/$APP_NAME" # Use absolute path
    exit 1
fi

echo ""
