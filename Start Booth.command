#!/bin/bash
# Double-click this file to start Booth. Close the window to stop it.
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ] || [ ! -s models/kokoro-v1.0.onnx ]; then
  echo "First run: setting things up. This happens once."
  bash ./setup.sh || { echo; echo "Setup did not finish. Read the message above, fix it, and try again."; read -n 1; exit 1; }
fi
if lsof -i :7863 -sTCP:LISTEN >/dev/null 2>&1; then
  echo "Booth is already running. Opening it..."
  open "http://127.0.0.1:7863"
  exit 0
fi
# lower priority keeps the rest of the Mac responsive while voices render
exec nice -n 10 .venv/bin/python server.py
