# integrations/ngrok_manager.py
from pyngrok import ngrok, conf
import logging
import socket
import time
import requests
from .config import NGROK_AUTHTOKEN
from . import config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ngrok_manager")

def wait_for_server(port, timeout=20):
    """
    Waits for the local server to be ready on the specified port.
    Checks socket connectivity first, then health endpoint.
    """
    start_time = time.time()
    url = f"http://127.0.0.1:{port}/health"
    
    logger.info(f"Checking server readiness on port {port} (timeout: {timeout}s)...")
    
    while time.time() - start_time < timeout:
        # 1. Socket Check
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        try:
            result = sock.connect_ex(('127.0.0.1', port))
            if result == 0:
                # Socket is open, now check application readiness
                try:
                    response = requests.get(url, timeout=1)
                    if response.status_code == 200:
                        logger.info(f"✓ Server ready on port {port}")
                        return True
                    else:
                        logger.warning(f"Server socket open but health check returned {response.status_code}")
                except requests.RequestException:
                    pass # App might be starting up
        except Exception as e:
            logger.debug(f"Socket check failed: {e}")
        finally:
            sock.close()
                
        time.sleep(1)
        elapsed = int(time.time() - start_time)
        logger.info(f"Waiting for server... ({elapsed}s elapsed)")

    logger.error(f"✗ Timeout waiting for server on port {port} after {timeout} seconds")
    return False

def start_ngrok(port):
    """Starts an ngrok tunnel to the local endpoint on the specified port."""
    if not port:
        logger.error("No port specified for Ngrok tunnel.")
        return None
        
    if not NGROK_AUTHTOKEN:
        logger.error("NGROK_AUTHTOKEN not found in environment. Please add it to .env")
        return None

    # Readiness Gate
    if not wait_for_server(port):
        logger.error(f"Server not reachable on port {port}. Aborting Ngrok start.")
        return None

    try:
        # Set auth token
        ngrok.set_auth_token(NGROK_AUTHTOKEN)
        
        # Start tunnel
        public_url = ngrok.connect(port).public_url
        logger.info(f"Ngrok tunnel started: {public_url} -> localhost:{port}")
        return public_url
    except Exception as e:
        logger.error(f"Failed to start ngrok tunnel: {e}")
        return None

def stop_ngrok():
    """Stops all active ngrok tunnels."""
    try:
        ngrok.kill()
        logger.info("Ngrok tunnels stopped.")
        return True
    except Exception as e:
        logger.error(f"Failed to stop ngrok: {e}")
        return False

def is_running():
    """Checks if there are active ngrok tunnels."""
    try:
        tunnels = ngrok.get_tunnels()
        return len(tunnels) > 0
    except:
        return False

if __name__ == "__main__":
    url = start_ngrok()
    if url:
        print(f"NGROK_URL={url}")
        # Keep alive if run directly
        import time
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            stop_ngrok()
