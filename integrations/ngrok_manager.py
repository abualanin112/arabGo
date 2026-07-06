# integrations/ngrok_manager.py
import logging
import socket
import time
import requests
import subprocess
import os
import urllib.request
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ngrok_manager")

_tunnel_process = None

def wait_for_server(port, timeout=20):
    """
    Waits for the local server to be ready on the specified port.
    Checks socket connectivity first, then health endpoint.
    """
    start_time = time.time()
    url = f"http://127.0.0.1:{port}/health"
    
    logger.info(f"Checking server readiness on port {port} (timeout: {timeout}s)...")
    
    while time.time() - start_time < timeout:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        try:
            result = sock.connect_ex(('127.0.0.1', port))
            if result == 0:
                try:
                    response = requests.get(url, timeout=1)
                    if response.status_code == 200:
                        logger.info(f"✓ Server ready on port {port}")
                        return True
                except requests.RequestException:
                    pass 
        except Exception as e:
            pass
        finally:
            sock.close()
                
        time.sleep(1)
    logger.error(f"✗ Timeout waiting for server on port {port}")
    return False

def start_ngrok(port):
    """Starts a Cloudflare tunnel (replacing Ngrok due to ISP blocks)."""
    global _tunnel_process
    if not port:
        logger.error("No port specified for tunnel.")
        return None

    if not wait_for_server(port):
        logger.error(f"Server not reachable on port {port}. Aborting tunnel start.")
        return None

    try:
        # We download cloudflared directly since Ngrok is blocked by ISP/Antivirus
        exe_path = os.path.join(os.path.dirname(__file__), "cloudflared.exe")
        if not os.path.exists(exe_path):
            logger.info("Downloading Cloudflare Tunnel binary (one-time setup)...")
            urllib.request.urlretrieve("https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe", exe_path)
            logger.info("Download complete.")
            
        logger.info("Starting Cloudflare Tunnel...")
        _tunnel_process = subprocess.Popen(
            [exe_path, "tunnel", "--url", f"http://127.0.0.1:{port}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        
        start_time = time.time()
        url = None
        while time.time() - start_time < 20:
            line = _tunnel_process.stderr.readline()
            if line:
                match = re.search(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com', line)
                if match:
                    url = match.group(0)
                    logger.info(f"Cloudflare Tunnel started: {url}")
                    return url
            else:
                time.sleep(0.5)
                
        logger.error("Failed to extract URL from Cloudflare Tunnel logs.")
        return None
    except Exception as e:
        logger.error(f"Failed to start tunnel: {e}")
        return None

def stop_ngrok():
    """Stops all active tunnels."""
    global _tunnel_process
    try:
        if _tunnel_process:
            _tunnel_process.terminate()
            _tunnel_process = None
            logger.info("Tunnel stopped.")
        return True
    except Exception as e:
        logger.error(f"Failed to stop tunnel: {e}")
        return False

def is_running():
    global _tunnel_process
    return _tunnel_process is not None and _tunnel_process.poll() is None
