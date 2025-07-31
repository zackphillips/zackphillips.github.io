import json
import requests
import subprocess
from datetime import datetime
from pathlib import Path

SIGNALK_URL = "http://localhost:3000/signalk/v1/api/vessels/self"  # adjust if needed
OUTPUT_FILE = Path("./signalk_latest.json")

def fetch_blob() -> dict:
    resp = requests.get(SIGNALK_URL)
    resp.raise_for_status()
    return resp.json()

def git_reset():
    subprocess.run(["git", "fetch", "--all"], check=True)
    subprocess.run(["git", "reset", "--hard", "origin/main"], check=True)

def git_push(file_path: Path):
    subprocess.run(["git", "add", str(file_path)], check=True)
    subprocess.run(["git", "commit", "--amend", "-m", f"Auto update {datetime.now().isoformat()}"], check=True)
    subprocess.run(["git", "push", "--force"], check=True)

def main():
    git_reset()
    blob = fetch_blob()
    OUTPUT_FILE.write_text(json.dumps(blob, indent=2))
    git_push(OUTPUT_FILE)

if __name__ == "__main__":
    main()
