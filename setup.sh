#!/usr/bin/env bash
# One-time setup. Run this once from inside the project folder: bash setup.sh
set -e

echo "== Checking for Homebrew =="
if ! command -v brew >/dev/null 2>&1; then
  echo "Homebrew not found. Install it first: https://brew.sh"
  exit 1
fi

echo "== Checking for ffmpeg =="
if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "Installing ffmpeg via Homebrew..."
  brew install ffmpeg
else
  echo "ffmpeg already installed: $(ffmpeg -version | head -1)"
fi

echo "== Setting up Python virtual environment =="
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "Setup complete."
echo "Every time you use this project, run:  source .venv/bin/activate"
