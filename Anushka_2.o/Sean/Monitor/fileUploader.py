import requests
import sys
import os
import datetime
from pathlib import Path

url = 'http://10.21.69.5:3000/convo-log'  # the URL of the endpoint on the server
REPO_ROOT = Path(__file__).resolve().parents[2]
MONITOR_DIR = REPO_ROOT / "Sean" / "Monitor"
file_path = MONITOR_DIR / "Now.txt"  # the path to the file you want to upload
new_file_path = MONITOR_DIR / (
    "file_" + str(str(datetime.datetime.now()).replace(" ", "_").replace(":", "-").split(".")[0] + ".txt")
)
os.rename(str(file_path), str(new_file_path))

with new_file_path.open('rb') as file:
    response = requests.post(url, files={'file': file})

if response.ok:
    print('File uploaded successfully.')
else:
    print('Error uploading file:', response.reason)
