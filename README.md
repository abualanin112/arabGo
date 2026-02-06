# Subtitle Management & QA Tool (Human-in-the-Loop)

A precision tool for managing, validating, and applying manual subtitle translations.

## Core Purpose

This software acts as a middleman between a human translator and subtitle files. It ensures that while the human focuses on translation, the software handles the **formatting, timing preservation, and structural integrity**.

## Usage Instructions

1.  **Scan**: Click "Scan Folder" and select your project root.
2.  **Select**: Click a file in the left sidebar. The tool will automatically split large files into **Safe Chunks** (~80 blocks).
3.  **Navigation**: Use the **Next >** / **< Prev** buttons or select a chunk from the dropdown.
4.  **Chunk Size**: You can adjust the "Chunk Size" (20-100) from the sidebar at any time.
5.  **Copy**: Click "Copy Current Chunk".
6.  **Translate**: Get your translation done manually (e.g., in ChatGPT).
7.  **Paste**: Paste the translation into the bottom area. Ensure each line starts with the correct `[ID]`.
8.  **Save Chunk**: Click **"1. Save Chunk to Session"**. This stores the translation in memory.
9.  **Complete All**: Repeat for all chunks. Check the status indicator (e.g., "3/5 chunks completed").
10. **Final Save**: Once all chunks are done, click **"2. Final Save to Disk"**.

## Why Chunking?

AI models (like ChatGPT) often lose data or hallucinate indices when processing more than 100 subtitle lines at once. By forcing a **Safe Chunk size (default: 50)**, we ensure 100% data integrity and allow for strict per-block validation.

## Rules of Operation

- **Advanced VTT Support**:
  - Automatically normalizes WebVTT files to SRT.
  - Detects VTT content even if mislabeled as `.srt`.
  - Fixes "Short Timestamps" (e.g., `00:05.189`) automatically.

- **Validation Rules**:
  - **ERROR**: Block count mismatch or ID mismatch.
  - **ERROR**: Translation contains English characters (Strict Mode).
  - **ERROR**: Empty blocks (previously a warning).
  - **Auto-Copy**: If validation fails, the original chunk is automatically copied to clipboard for quick retry.

- **Dynamic Rechunking (New!)**:
  - You can change the "Chunk Size" (20, 25, 50, 75, 100) **mid-session**.
  - The system will safely **reorganize your progress** and preserve completed translations.
  - Any partial overlaps will be marked as PENDING for review.

- **Safety**: The original file is only replaced if the new version is successfully written to a temporary location first.

## Optional: AI-Assisted Automation

arabGo includes an optional integration layer for AI-assisted translation (e.g., via ChatGPT).

### 1. Setup

**Prerequisites:**

- [ngrok](https://ngrok.com/) installed on your machine.
- An ngrok account with an authtoken.

**Configuration:**

1. Create a `.env` file in the project root.
2. Add your ngrok authtoken:
   ```env
   NGROK_AUTHTOKEN=your_authtoken_here
   ```

### 2. Using AI Automation

1. **Launch arabGo**: Run `python main.py` as usual.
2. **Enable Mode**: Check the "Enable AI Automation" checkbox in the editor.
3. **Start Server**: Click "1. Start Server". This opens a local endpoint on port `8765`.
4. **Start Ngrok**: Click "2. Start Ngrok". This generates a public URL.
5. **Configure ChatGPT**:
   - Copy the Ngrok URL.
   - Use it in a ChatGPT Action to POST translations to: `{NGROK_URL}/api/submit_translation`
   - Payload format: `{"translation": "[1] Your translation here..."}`
   - **Note**: `chunk_id` is optional. The application will automatically select the next pending chunk.
6. **Auto-Injection**: When a translation is received with a valid signature, the app automatically selects the matching chunk and injects the translation.
7. **Full Automation (Optional)**:
   - Check **"Full Automation (Auto-Save & Finalize)"**.
   - Validated translations will be saved automatically.
   - The final merged file will be generated automatically once all chunks are done.
   - Manual buttons are disabled in this mode to prevent conflicts.
8. **Validation & Save (Manual)**: If Full Automation is OFF, review the injected text and click "Save Chunk to Session" manually.

### 3. Safety & Control

- **Isolation**: The automation layer is completely decoupled from core logic.
- **Opt-In**: You must explicitly start the server and tunnel for each session.
- **No Auto-Save**: All AI translations require human review and a manual save action.
- **Graceful Failure**: If automation fails, the manual copy/paste workflow remains fully functional.

## Setup & Activation

### 1. Enable Virtual Environment

Before running the app, activate the virtual environment:

**CMD:**

```cmd
.venv\Scripts\activate
```

**PowerShell:**

```powershell
.\.venv\Scripts\Activate.ps1
```

### 2. Install Dependencies

If you haven't already, install the required packages:

```bash
pip install -r requirements.txt
```

## Running the App

After activation, run:

```bash
python main.py
```

## Running Tests

### Core Tests

```bash
python -m unittest tests/test_subtitle_tool.py
```

### Automation Tests

```bash
python -m unittest discover tests
```
