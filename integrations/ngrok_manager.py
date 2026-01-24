# integrations/ngrok_manager.py
from pyngrok import ngrok, conf
import logging
from .config import NGROK_AUTHTOKEN, ENDPOINT_PORT

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ngrok_manager")

def start_ngrok(port=None):
    """Starts an ngrok tunnel to the local endpoint."""
    if port is None:
        port = ENDPOINT_PORT
        
    if not NGROK_AUTHTOKEN:
        logger.error("NGROK_AUTHTOKEN not found in environment. Please add it to .env")
        return None

    try:
        # Set auth token
        ngrok.set_auth_token(NGROK_AUTHTOKEN)
        
        # Start tunnel
        # Note: In free tier, we only get 1 tunnel
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
