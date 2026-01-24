# arabGo AI Automation Guide

This guide explains how to use the optional AI-assisted translation features in arabGo.

## 1. Setup

### Prerequisites

- [ngrok](https://ngrok.com/) installed on your machine.
- An ngrok account with an authtoken.

### Configuration

1. Create a `.env` file in the project root.
2. Add your ngrok authtoken:
   ```env
   NGROK_AUTHTOKEN=your_authtoken_here
   ```

## 2. Using AI Automation

1. **Launch arabGo**: Run `python main.py` as usual.
2. **Enable Mode**: Check the "Enable AI Automation" checkbox in the editor.
3. **Start Server**: Click "1. Start Server". This opens a local endpoint on port `8765`.
4. **Start Ngrok**: Click "2. Start Ngrok". This generates a public URL (e.g., `https://xxxx.ngrok-free.app`).
5. **Configure ChatGPT**:
   - Copy the Ngrok URL.
   - Use it in a ChatGPT Action or custom script to POST translations to:
     `{NGROK_URL}/api/submit_translation`
   - Payload format:
     ```json
     {
       "chunk_id": 1,
       "translation": "[1] Your Arabic translation here..."
     }
     ```
6. **Auto-Injection**: When ChatGPT sends a translation, it will automatically appear in the translation text box **if that chunk is currently selected**.
7. **Validation**: The tool will automatically run its standard validation.
8. **Save**: Click "Save Chunk to Session" manually to commit the AI translation.

## 3. Safety Mechanisms

- **Isolation**: The automation layer lives in `/integrations` and is completely decoupled from core logic.
- **Opt-In**: You must explicitly enable automation and start the server/tunnel.
- **No Auto-Save**: Received translations are injected into the UI for review. The user MUST click "Save" manually.
- **Validation**: Every AI translation passes through the same strict validation rules as manual entry.
- **Control**: You can stop ngrok or the endpoint server at any time without affecting your manual progress.

## 4. Troubleshooting

- **Ngrok fails**: Ensure your authtoken is correct in `.env`.
- **Server fails**: Check if port `8765` is already in use.
- **Injection fails**: Ensure the correct chunk is selected in the dropdown before the AI sends data.
