"""Startup script: wait for DB, import data if needed, then run the web server."""
import os
import socket
import subprocess
import sys
import time

def wait_for_db(timeout=30):
    """Wait for the database to accept connections."""
    db_url = os.environ.get("DATABASE_URL", "")
    # Extract host:port from DATABASE_URL
    if "@" in db_url and "/" in db_url.split("@")[-1]:
        hostport = db_url.split("@")[-1].split("/")[0]
        host, port = hostport.split(":") if ":" in hostport else (hostport, "5432")
    else:
        host, port = "db", "5432"

    print(f"Waiting for database at {host}:{port}...")
    start = time.time()
    while time.time() - start < timeout:
        try:
            sock = socket.create_connection((host, int(port)), timeout=2)
            sock.close()
            print("Database is ready.")
            return
        except (ConnectionRefusedError, OSError):
            time.sleep(1)
    print("WARNING: Database not reachable after timeout, continuing anyway...")


print("=== Polok startup ===")
wait_for_db()

print("Running data import (skips if data already present)...")
subprocess.run([sys.executable, "import_data.py"], check=True)

print("Starting web server...")
subprocess.run(
    [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"],
    check=True,
)
