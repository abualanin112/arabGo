# integrations/endpoint_server.py
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
import uvicorn
import logging
from typing import Optional as Opt
from .queue_handler import push_translation
from . import config
from . import session_manager
import socket

app = FastAPI(title="arabGo AI Automation Endpoint")

# Configure logging
logger = logging.getLogger("endpoint_server")

class TranslationSubmission(BaseModel):
    chunk_id: Opt[int] = None
    translation: str

@app.post("/api/submit_translation")
async def submit_translation(submission: TranslationSubmission, request: Request):
    # Verify session is active
    sm = session_manager.get_session_manager()
    if not sm:
        logger.error("Rejecting submission: No active session in arabGo.")
        raise HTTPException(
            status_code=400, 
            detail="No active translation session in arabGo. Please open a subtitle file first."
        )

    # Basic size check
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > config.MAX_REQUEST_SIZE:
        logger.error(f"Payload too large: {content_length} bytes")
        raise HTTPException(status_code=413, detail="Payload too large")

    logger.info(f"Received translation submission. Manual chunk_id: {submission.chunk_id}")
    
    # Push to queue for UI processing
    push_translation(submission.chunk_id, submission.translation)
    
    return {
        "status": "success", 
        "message": "Translation received and queued. Check arabGo UI for injection status."
    }

@app.get("/health")
async def health_check():
    sm = session_manager.get_session_manager()
    if sm:
        session_info = sm.get_session_info()
        return {
            "status": "healthy",
            "session": session_info
        }
    return {
        "status": "healthy",
        "session": None,
        "message": "No active translation session"
    }

def find_available_port(start_port, max_tries=10):
    for port in range(start_port, start_port + max_tries):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError("Could not find an available port.")

def start_server(port: int):
    logging.basicConfig(level=logging.INFO)
    try:
        # Note: We do NOT mutate config.ENDPOINT_PORT here.
        # The port is passed explicitly from the orchestrator.
        
        logger.info(f"Starting endpoint server on port {port}")
        uvicorn.run(app, host="127.0.0.1", port=port)
    except Exception as e:
        logger.error(f"Failed to start server: {e}")

if __name__ == "__main__":
    start_server(config.ENDPOINT_PORT)
