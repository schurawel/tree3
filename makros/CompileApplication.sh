#!/bin/bash

# CompileApplication.sh - A script to compile the Python application using PyInstaller

MAIN_SCRIPT="main.py" # Reverted to main.py, assuming it's at the project root
APP_NAME="ResearchGuideApp" # Name of the output executable
OUTPUT_DIR="./dist"
BUILD_DIR="./build_pyinstaller" # Changed from ./build
SPEC_FILE="${APP_NAME}.spec"
VENV_DIR=".venv" # Define the virtual environment directory

echo "---------------------------------------------------------------------"
echo "Python Application Compiler using PyInstaller"
echo "---------------------------------------------------------------------"
echo ""
echo "This script will attempt to compile '$MAIN_SCRIPT' into a standalone"
echo "executable named '$APP_NAME' in the '$OUTPUT_DIR' directory."
echo ""
echo "Prerequisites:"
echo "  - A Python virtual environment should exist at '$VENV_DIR'."
echo "  - PyInstaller must be installed IN THE VIRTUAL ENVIRONMENT."
echo "    (Activate venv: 'source $VENV_DIR/bin/activate', then 'pip install pyinstaller')"
echo "  - You should run this script from the root of your project directory."
echo "  - The Sphinx documentation must be built first, and be available at './build_docs'."
echo "    (e.g., by running 'make html' in your Sphinx 'docs' directory if it's configured to output to '../build_docs')" # Corrected
echo "  - If Sphinx is also used, ensure its build directory does not conflict."
echo "    This script changes PyInstaller's build path to '$BUILD_DIR'."
echo ""

# Check if the virtual environment directory exists
if [ ! -d "$VENV_DIR" ]; then
    echo "ERROR: Virtual environment directory '$VENV_DIR' not found."
    echo "Please create and activate your virtual environment, then install PyInstaller within it."
    exit 1
fi

# Activate the virtual environment
echo "Activating virtual environment: $VENV_DIR/bin/activate"
source "$VENV_DIR/bin/activate"

# Check if PyInstaller is installed (basic check within the venv)
if ! command -v pyinstaller &> /dev/null
then
    echo "ERROR: PyInstaller command could not be found AFTER activating the virtual environment."
    echo "Please ensure PyInstaller is installed in '$VENV_DIR' (e.g., 'pip install pyinstaller')."
    # Deactivate venv before exiting if activation was successful
    deactivate
    exit 1
fi
echo "Virtual environment activated and PyInstaller found."
echo ""

# Check if Sphinx documentation directory exists and is accessible
SPHINX_DOCS_DIR_RELATIVE="./build_docs" # Removed trailing space
# Resolve to an absolute path
SPHINX_DOCS_DIR_ABSOLUTE="$(readlink -m "$SPHINX_DOCS_DIR_RELATIVE")"

echo "Verifying Sphinx documentation source directory..."
echo "Expected relative path for source: '$SPHINX_DOCS_DIR_RELATIVE'"
echo "Resolved absolute path for source: '$SPHINX_DOCS_DIR_ABSOLUTE'"

echo "Sphinx documentation source directory '$SPHINX_DOCS_DIR_ABSOLUTE' confirmed to exist and be readable."
echo "Listing contents of '$SPHINX_DOCS_DIR_ABSOLUTE':"
ls -ldA "$SPHINX_DOCS_DIR_ABSOLUTE" # Show directory itself
ls -lA "$SPHINX_DOCS_DIR_ABSOLUTE"  # Show contents

# Specifically check for the html subdirectory and index.html within the source
SPHINX_HTML_SUBDIR="$SPHINX_DOCS_DIR_ABSOLUTE/html"
SPHINX_INDEX_HTML_IN_SOURCE="$SPHINX_HTML_SUBDIR/index.html"

echo "Checking for '$SPHINX_HTML_SUBDIR' within the source..."
if [ ! -d "$SPHINX_HTML_SUBDIR" ]; then
    echo "ERROR: Expected 'html' subdirectory not found in source '$SPHINX_DOCS_DIR_ABSOLUTE'."
    deactivate
    exit 1
fi
echo "'$SPHINX_HTML_SUBDIR' found. Listing contents:"
ls -lA "$SPHINX_HTML_SUBDIR"

echo "Checking for '$SPHINX_INDEX_HTML_IN_SOURCE'..."
if [ ! -f "$SPHINX_INDEX_HTML_IN_SOURCE" ]; then
    echo "ERROR: Expected 'index.html' not found in source '$SPHINX_HTML_SUBDIR'."
    deactivate
    exit 1
fi
echo "'$SPHINX_INDEX_HTML_IN_SOURCE' found."
echo "Verification of Sphinx documentation source directory successful."
echo ""

echo "Cleaning up previous PyInstaller build artifacts (if any)..."
rm -rf "$OUTPUT_DIR"
rm -rf "$BUILD_DIR" # Ensure this uses the new build directory name
rm -f "$SPEC_FILE"
echo "Cleanup complete."
echo ""

echo "Starting PyInstaller compilation (using Python from virtual environment)..."
echo "This might take a few minutes."
echo ""

# PyInstaller command:
# --add-data for build_docs is REMOVED. We will copy it manually later.
pyinstaller --noconfirm --log-level=INFO --onedir --name "$APP_NAME" \
            --workpath "$BUILD_DIR" \
            --hidden-import=ResearchGuideUnearth \
            --paths . \
            "$MAIN_SCRIPT"

PYINSTALLER_EXIT_CODE=$?

# Deactivate the virtual environment
echo ""
echo "Deactivating virtual environment..."
deactivate

# Check the exit status of PyInstaller
if [ $PYINSTALLER_EXIT_CODE -eq 0 ]; then
  echo ""
  echo "---------------------------------------------------------------------"
  echo "PyInstaller Compilation Successful!"
  echo "---------------------------------------------------------------------"
  
  # Manually copy the Sphinx documentation into the bundle
  echo "Copying Sphinx documentation ('$SPHINX_DOCS_DIR_ABSOLUTE') into the application bundle..."
  DEST_DOCS_PATH="$OUTPUT_DIR/$APP_NAME/build_docs" 
  
  # Ensure the parent directory of DEST_DOCS_PATH exists (it should, it's $OUTPUT_DIR/$APP_NAME)
  if [ ! -d "$OUTPUT_DIR/$APP_NAME" ]; then
    echo "ERROR: Output application directory '$OUTPUT_DIR/$APP_NAME' does not exist after PyInstaller success. This is unexpected."
  else
    # Primary copy to <bundle_root>/build_docs
    cp -r "$SPHINX_DOCS_DIR_ABSOLUTE" "$DEST_DOCS_PATH"
    CP_EXIT_CODE=$?
    if [ $CP_EXIT_CODE -eq 0 ]; then
      echo "Sphinx documentation successfully copied to '$DEST_DOCS_PATH'."
      echo "Verifying copied documentation..."
      ls -ldA "$DEST_DOCS_PATH"
      ls -lA "$DEST_DOCS_PATH/html"

      # Copy to sys._MEIPASS location (already includes _internal)
      INTERNAL_DEST_DOCS_PATH="$OUTPUT_DIR/$APP_NAME/_internal/build_docs"
      echo "Copying documentation to internal location: $INTERNAL_DEST_DOCS_PATH"
      mkdir -p "$INTERNAL_DEST_DOCS_PATH"
      cp -r "$SPHINX_DOCS_DIR_ABSOLUTE" "$INTERNAL_DEST_DOCS_PATH"
      INTERNAL_CP_EXIT_CODE=$?
      if [ $INTERNAL_CP_EXIT_CODE -eq 0 ]; then
        echo "Documentation successfully copied to internal location: $INTERNAL_DEST_DOCS_PATH"
        ls -ldA "$INTERNAL_DEST_DOCS_PATH"
      else
        echo "WARNING: Failed to copy documentation to internal location. Exit code: $INTERNAL_CP_EXIT_CODE"
      fi

      # Copy to a shared system location that's accessible outside the bundle - with fixed permissions
      SHARED_DOCS_DIR="$HOME/.local/share/ResearchGuideApp/docs"
      echo "Copying documentation to shared location: $SHARED_DOCS_DIR"
      mkdir -p "$SHARED_DOCS_DIR"
      cp -r "$SPHINX_HTML_SUBDIR/." "$SHARED_DOCS_DIR/html/"
      SHARED_CP_EXIT_CODE=$?
      if [ $SHARED_CP_EXIT_CODE -eq 0 ]; then
        echo "Documentation successfully copied to shared location: $SHARED_DOCS_DIR/html"
        # Ensure it's readable by everyone
        chmod -R 755 "$SHARED_DOCS_DIR"
        ls -ldA "$SHARED_DOCS_DIR"
        ls -lA "$SHARED_DOCS_DIR/html"
      else
        echo "WARNING: Failed to copy documentation to shared location. Exit code: $SHARED_CP_EXIT_CODE"
      fi
    else
      echo "ERROR: Failed to copy Sphinx documentation to primary '$DEST_DOCS_PATH'. Exit code: $CP_EXIT_CODE"
      echo "The application is built, but documentation will be missing."
    fi
  fi

  echo ""
  echo "The application directory is located at: $OUTPUT_DIR/$APP_NAME/"
  echo "The executable is at: $OUTPUT_DIR/$APP_NAME/$APP_NAME"
  echo ""
  echo "To run the compiled application (on this system):"
  echo "  cd $OUTPUT_DIR/$APP_NAME"
  echo "  ./$APP_NAME"
  echo ""
  echo "NOTE for GUI applications (like PyQt6):"
  echo "  - Ensure all necessary system libraries are available on the target system if you distribute this executable."
  echo "  - You might need to adjust PyInstaller options (e.g., --hidden-import, --add-data) if the application"
  echo "    doesn't run correctly due to missing modules or files."
  echo "  - Sphinx users: If you still have conflicts, ensure Sphinx is configured"
  echo "    to use a different output directory (e.g., in its conf.py or Makefile)."
else
  echo ""
  echo "---------------------------------------------------------------------"
  echo "ERROR: PyInstaller Compilation Failed. Exit code: $PYINSTALLER_EXIT_CODE"
  echo "---------------------------------------------------------------------"
  echo "Please check the output above for specific error messages from PyInstaller."
  echo "Common issues include missing dependencies, incorrect paths, or problems with specific packages."
fi

echo ""
echo "---------------------------------------------------------------------"
echo "This script compiles the application for your current host system."
echo "If you want to run this compiled executable inside a Docker container,"
echo "you would typically integrate the PyInstaller build process into your Dockerfile."
echo "---------------------------------------------------------------------"
