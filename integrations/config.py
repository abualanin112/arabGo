# integrations/config.py
import os
from dotenv import load_dotenv

load_dotenv()

ENDPOINT_PORT = int(os.getenv("ENDPOINT_PORT", 8765))
NGROK_AUTHTOKEN = os.getenv("NGROK_AUTHTOKEN", "")
MAX_REQUEST_SIZE = 51200  # 50KB
RATE_LIMIT = "10/minute"
ENABLE_AUTOMATION = False # Controlled via UI
