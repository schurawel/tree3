#!/bin/bash

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Change to the script's directory to ensure relative paths in python script work
cd "$SCRIPT_DIR"

source ../.venv/bin/activate

# Execute the Python script
# Ensure python3 is in your PATH or use the full path to the python executable
python ../ResearchGuidePackage/FrontendModule/frontend.py & python ../ResearchGuidePackage/BackendModule/backend.py