import urllib.request
import os
import subprocess
import time
import re
import sys

exe_path = "cloudflared.exe"

if not os.path.exists(exe_path):
    print("Downloading cloudflared.exe...")
    urllib.request.urlretrieve("https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe", exe_path)
    print("Download complete.")

print("Starting cloudflared tunnel...")
proc = subprocess.Popen(
    [exe_path, "tunnel", "--url", "http://127.0.0.1:8765"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    creationflags=subprocess.CREATE_NO_WINDOW
)

start_time = time.time()
url = None
# Cloudflared outputs the URL in stderr
while time.time() - start_time < 15:
    line = proc.stderr.readline()
    if line:
        print(line.strip())
        match = re.search(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com', line)
        if match:
            url = match.group(0)
            break
    else:
        time.sleep(0.5)

if url:
    print(f"\nSUCCESS! URL is: {url}")
else:
    print("\nFAILED to extract URL.")

proc.terminate()
