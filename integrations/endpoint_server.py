# integrations/endpoint_server.py
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
import uvicorn
import logging
from .queue_handler import push_translation
from .config import ENDPOINT_PORT, MAX_REQUEST_SIZE

app = FastAPI(title="arabGo AI Automation Endpoint")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("endpoint_server")

class TranslationSubmission(BaseModel):
    chunk_id: int
    translation: str

@app.post("/api/submit_translation")
async def submit_translation(submission: TranslationSubmission, request: Request):
    # Basic size check (though Pydantic/FastAPI has some defaults)
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_REQUEST_SIZE:
        logger.error(f"Payload too large: {content_length} bytes")
        raise HTTPException(status_code=413, detail="Payload too large")

    logger.info(f"Received translation for chunk {submission.chunk_id}")
    
    # Push to queue for UI processing
    push_translation(submission.chunk_id, submission.translation)
    
    return {"status": "success", "message": f"Translation for chunk {submission.chunk_id} queued"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

def start_server():
    logger.info(f"Starting endpoint server on port {ENDPOINT_PORT}")
    uvicorn.run(app, host="127.0.0.1", port=ENDPOINT_PORT)

if __name__ == "__main__":
    start_server()
