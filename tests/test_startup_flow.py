import threading
import time
import requests
import logging
import sys
import os

# Add project root to sys.path to allow importing modules from parent directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from integrations import ngrok_manager, endpoint_server, config

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_startup")

def simulate_slow_server_startup(port):
    """Simulates a server that takes a few seconds to start."""
    logger.info(f"TEST: Starting server simulation on port {port} in 3 seconds...")
    time.sleep(3)
    endpoint_server.start_server(port)

def test_readiness_check():
    """Tests if wait_for_server correctly waits for the server."""
    port = endpoint_server.find_available_port(8888)
    logger.info(f"TEST: Selected port {port}")
    
    # Start server in background with delay
    t = threading.Thread(target=simulate_slow_server_startup, args=(port,), daemon=True)
    t.start()
    
    logger.info("TEST: Attempting to wait for server...")
    ready = ngrok_manager.wait_for_server(port, timeout=10)
    
    if ready:
        logger.info("TEST: SUCCESS! Server detected as ready.")
    else:
        logger.error("TEST: FAILURE! Timeout waiting for server.")

if __name__ == "__main__":
    test_readiness_check()
