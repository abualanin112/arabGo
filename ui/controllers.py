from . import utils
import os
import threading
import time
import tkinter as tk
from integrations import endpoint_server, ngrok_manager, queue_handler

class PipelineController:
    def __init__(self, view):
        self.view = view
        self.server_thread = None
        self.polling_active = False

    def log(self, message):
        timestamp = utils.get_timestamp()
        for line in message.split('\n'):
            if line.strip():
                self.view.append_log(f"{timestamp} {line.strip()}")

    def refresh_dashboard(self):
        # Auto-convert VTTs in en_srt before updating stats
        utils.check_and_convert_imports(self.log)
        
        stats = utils.get_stats()
        self.view.update_stats(stats)
        
        base_path = utils.get_base_path()
        pending_file = os.path.join(base_path, "qc", "pending.txt")
        if os.path.exists(pending_file):
            try:
                with open(pending_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    self.view.update_pending_text(content if content.strip() else "All chunks completed!")
            except Exception as e:
                self.view.update_pending_text(f"Error reading pending.txt: {e}")
        else:
            self.view.update_pending_text("No pending.txt found. Run 'Check Status' first.")

    def run_split(self):
        # Ensure imports are converted before splitting
        utils.check_and_convert_imports(self.log)
        if utils.run_script("split.py", self.log):
            self.refresh_dashboard()

    def run_status(self):
        if utils.run_script("status.py", self.log):
            self.refresh_dashboard()

    def run_consistency(self):
        utils.run_script("check_consistency.py", self.log)

    def run_merge(self):
        if utils.run_script("merge.py", self.log):
            self.refresh_dashboard()
            # After successful merge, offer/inform about export?
            # Or just wait for user to click an export button
            
    def run_export_vtt(self):
        base_path = utils.get_base_path()
        final_dir = os.path.join(base_path, "final")
        if not os.path.exists(final_dir):
            self.log("ERROR: final/ directory not found.")
            return

        final_files = [f for f in os.listdir(final_dir) if f.lower().endswith(".ar.final.srt")]
        if not final_files:
            self.log("ERROR: No merged SRT files found in final/ to export.")
            return

        for srt_file in final_files:
            srt_path = os.path.join(final_dir, srt_file)
            utils.export_to_vtt(srt_path, self.log)

    # --- Automation Logic ---
    
    def toggle_automation(self, enabled):
        state = tk.NORMAL if enabled else tk.DISABLED
        self.view.start_auto_btn.config(state=state)
        self.view.start_ngrok_btn.config(state=state)
        self.view.stop_auto_btn.config(state=state)
        self.view.copy_url_btn.config(state=state)
        
        if enabled and not self.polling_active:
            self.start_queue_polling()
        elif not enabled:
            self.polling_active = False

    def start_endpoint_server(self):
        if self.server_thread and self.server_thread.is_alive():
            self.log("Endpoint server is already running.")
            return

        self.log("Starting endpoint server...")
        self.server_thread = threading.Thread(target=endpoint_server.start_server, daemon=True)
        self.server_thread.start()
        self.view.automation_vars["status"].set("Server Running")
        self.log("Endpoint server started on localhost:8765")

    def start_ngrok(self):
        self.log("Starting ngrok tunnel...")
        # Run in thread so it doesn't block UI if it takes time
        def do_start():
            url = ngrok_manager.start_ngrok()
            if url:
                self.view.automation_vars["url"].set(url)
                self.log(f"Ngrok active: {url}")
            else:
                self.log("CRITICAL: Failed to start ngrok. Check .env for NGROK_AUTHTOKEN.")

        threading.Thread(target=do_start, daemon=True).start()

    def stop_automation_layer(self):
        self.log("Stopping automation layer...")
        ngrok_manager.stop_ngrok()
        self.view.automation_vars["url"].set("Inactive")
        self.view.automation_vars["status"].set("Stopped")
        self.log("Ngrok stopped. Endpoint server will stop on app exit.")

    def start_queue_polling(self):
        self.polling_active = True
        self.log("AI automation queue polling active.")
        self._poll_queue()

    def _poll_queue(self):
        if not self.polling_active:
            return

        item = queue_handler.pop_translation()
        if item:
            self.log(f"AI: Received translation for chunk {item['chunk_id']}")
            # In a real app, we'd find the text box for this chunk.
            # But the current UI is a single "Pending Chunks" list.
            # For now, we append/replace in the manual translation area if it existed.
            # WAIT: The current UI doesn't have a translation text box yet!
            # It only has a "Pending Chunks" viewer.
            # I need to check where the user pastes the translation.
            pass

        # Poll again in 500ms
        self.view.after(500, self._poll_queue)

    def copy_to_clipboard(self, text):
        self.view.clipboard_clear()
        self.view.clipboard_append(text)
        self.log("URL copied to clipboard.")
