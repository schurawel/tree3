# Remove any existing pyenv
rm -rf "$HOME/.pyenv"

# Install dependencies for pyenv and Python building
echo "Installing dependencies..."
sudo apt-get update
sudo apt-get install -y make build-essential libssl-dev zlib1g-dev \
  libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm \
  libncursesw5-dev xz-utils tk-dev libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev

# Clone pyenv
git clone https://github.com/pyenv/pyenv.git "$HOME/.pyenv"

# Add to shell profile manually
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> "$HOME/.bashrc"
echo 'command -v pyenv >/dev/null || export PATH="$PYENV_ROOT/bin:$PATH"' >> "$HOME/.bashrc"
echo 'eval "$(pyenv init -)"' >> "$HOME/.bashrc"

# Set environment variables for current session
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"

# Verify pyenv is accessible
if ! command -v pyenv &> /dev/null; then
    echo "pyenv command not found. Using full path..."
    PYENV_BIN="$PYENV_ROOT/bin/pyenv"
    if [ ! -f "$PYENV_BIN" ]; then
        echo "ERROR: pyenv binary not found at $PYENV_BIN"
        exit 1
    fi
else
    PYENV_BIN="pyenv"
fi

# Initialize pyenv
eval "$("$PYENV_BIN" init -)"

# Find and install the latest stable Python version
echo "Finding latest Python version..."
LATEST_PYTHON=$("$PYENV_BIN" install --list | grep -v - | grep -v a | grep -v b | grep -v rc | grep -E '^  3\.[0-9]+\.[0-9]+$' | tail -1 | tr -d '[:space:]')

if [ -z "$LATEST_PYTHON" ]; then
    echo "Could not determine latest Python version. Defaulting to 3.12.3"
    LATEST_PYTHON="3.12.3"
fi

echo "Installing Python $LATEST_PYTHON..."
"$PYENV_BIN" install $LATEST_PYTHON
"$PYENV_BIN" global $LATEST_PYTHON

# Rehash to make sure shims are created
"$PYENV_BIN" rehash

# Verify installation
echo "Installed Python versions:"
"$PYENV_BIN" versions
echo "Current Python version:"
"$PYENV_BIN" exec python --version

echo "Installation complete. Python should now be available."
echo "To use in a new terminal, you'll need to restart your terminal or run:"
echo "source ~/.bashrc"