"""Startup script: import data if needed, then run the web server."""
import subprocess
import sys

print("=== Polok startup ===")
print("Running data import (skips if data already present)...")
subprocess.run([sys.executable, "import_data.py"], check=True)

print("Starting web server...")
subprocess.run(
    [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"],
    check=True,
)
