#!/bin/bash
#
# Shell script to run tests using the virtual environment
# This activates the venv first and then runs the test runner Python script

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "${SCRIPT_DIR}")"

# Activate the virtual environment
# The script assumes the venv is in a standard location; adjust path if needed
if [ -d "${PROJECT_ROOT}/venv" ]; then
    source "${PROJECT_ROOT}/venv/bin/activate"
elif [ -d "${PROJECT_ROOT}/.venv" ]; then
    source "${PROJECT_ROOT}/.venv/bin/activate"
else
    echo "Virtual environment not found. Please create or specify the correct path."
    exit 1
fi

# Execute the Python test runner script
python "${SCRIPT_DIR}/run_all_tests.py" "$@"

# Capture the exit code before deactivating
EXIT_CODE=$?

# Deactivate the virtual environment
deactivate

# Exit with the same status code as the Python script
exit $EXIT_CODE
