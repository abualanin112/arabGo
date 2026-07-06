import os
import queue
import threading
import time
import tkinter as tk
from integrations import endpoint_server, ngrok_manager, queue_handler, session_manager, local_translator
from tkinter import filedialog, messagebox
from core.file_ops import scan_directory_threaded, atomic_save
from core.vtt_converter import normalize_file
from core.domain import SubtitleDocument
from core.session import TranslationSession
from core.chunking import TranslationChunk

class UILogic:
    def __init__(self, view, root):
        self.view = view
        self.root = root
        self.file_map = {} # path -> SubtitleDocument
        
        # Automation state
        self.server_thread = None
        self.polling_active = False
        self.current_file = None
        self.session = None
        self.scan_queue = queue.Queue()
        
        # Bind UI events
        self.view.btn_select_dir.config(command=self.on_scan_clicked)
        self.view.btn_copy_all.config(command=self.on_copy_all)
        self.view.btn_save_chunk.config(command=self.on_save_chunk_clicked)
        self.view.btn_final_save.config(command=self.on_final_save_clicked)
        
        self.view.file_listbox.bind("<<ListboxSelect>>", self.on_file_selected)
        self.view.chunk_combo.bind("<<ComboboxSelected>>", self.on_chunk_selected)
        self.view.chunk_size_combo.bind("<<ComboboxSelected>>", self.on_chunk_size_changed)
        self.view.btn_paste_translation.config(command=self.on_paste_translation_clicked)
        # BIND PASTE EVENT FOR AUTOMATION
        self.view.txt_translation.bind("<<Paste>>", self.on_clipboard_paste)
        self.view.txt_translation.bind("<Control-v>", self.on_clipboard_paste)
        # BIND KEY RELEASE FOR LIVE EVALUATION
        self.view.txt_translation.bind("<KeyRelease>", self.on_text_edited)
        
        # Navigation Bindings
        self.view.btn_prev_chunk.config(command=self.on_prev_chunk)
        self.view.btn_next_chunk.config(command=self.on_next_chunk)
        
        # Bind Automation events
        self.view.auto_enable_check.config(command=self.toggle_automation)
        self.view.start_auto_btn.config(command=self.start_endpoint_server)
        self.view.start_ngrok_btn.config(command=self.start_ngrok)
        self.view.stop_auto_btn.config(command=self.stop_automation_layer)
        self.view.copy_url_btn.config(command=self.copy_url_to_clipboard)
        self.view.full_auto_check.config(command=self.toggle_automation)
        
        # Initial automation state
        self.toggle_automation()

    def on_scan_clicked(self):
        folder = filedialog.askdirectory()
        if not folder:
            return
        
        self.view.file_listbox.delete(0, tk.END)
        self.view.append_log(f"Scanning: {folder}")
        self.view.update_status("Scanning...", "blue")
        
        # Start threaded scan
        scan_directory_threaded(folder, self.scan_queue)
        self.root.after(100, self.poll_scan_results)

    def poll_scan_results(self):
        try:
            result = self.scan_queue.get_nowait()
            if result["type"] == "success":
                files = result["files"]
                self.view.append_log(f"Found {len(files)} subtitle files.")
                for f in files:
                    try:
                        is_vtt = f.lower().endswith(".vtt")
                        norm_path = normalize_file(f)
                        
                        if is_vtt:
                            self.view.append_log(f"Converted: {os.path.basename(f)} -> {os.path.basename(norm_path)}")
                            self.view.append_log(f"Original VTT deleted after successful validation.")
                        
                        self.view.file_listbox.insert(tk.END, norm_path)
                        
                        # If this file was already current_file, re-highlight and re-select it
                        if self.current_file == norm_path:
                            last_idx = self.view.file_listbox.size() - 1
                            self.view.file_listbox.selection_set(last_idx)
                            self.view.file_listbox.itemconfig(last_idx, bg="#cfe8fc", fg="black")

                    except Exception as e:
                        self.view.append_log(f"Error normalizing {os.path.basename(f)}: {e}")
                
                self.view.update_status("Scan Complete", "green")
            else:
                messagebox.showerror("Error", result["message"])
                self.view.update_status("Scan Failed", "red")
        except queue.Empty:
            self.root.after(100, self.poll_scan_results)

    def on_file_selected(self, event):
        selection = self.view.file_listbox.curselection()
        if not selection:
            return
        
        file_path = self.view.file_listbox.get(selection[0])
        self.current_file = file_path
        
        # UI Feedback: Reset all backgrounds and highlight the active one
        for i in range(self.view.file_listbox.size()):
            self.view.file_listbox.itemconfig(i, bg="white", fg="black")
        self.view.file_listbox.itemconfig(selection[0], bg="#cfe8fc", fg="black") # Light blue active indicator

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            doc = SubtitleDocument.from_srt(content)
            self.file_map[file_path] = doc
            
            # Initialize Session
            # Initialize Session with Configured Chunk Size
            chunk_size = self.view.chunk_size_var.get()
            self.session = TranslationSession(doc, max_blocks=chunk_size)
            
            # Note: We keep chunk_size_combo ENABLED to allow dynamic resizing
            
            # Initialize SessionManager for automation
            
            # Initialize SessionManager for automation
            sm = session_manager.initialize_session()
            for chunk in self.session.chunks:
                sm.initialize_chunk(chunk.signature)
            
            self.refresh_chunk_combo()
            
            self.view.update_status(f"Loaded {os.path.basename(file_path)}", "black")
            self.update_session_stats()
            
        except Exception as e:
            messagebox.showerror("Parse Error", f"Could not parse file: {e}")

    def refresh_chunk_combo(self):
        """Helper to rebuild the chunk combobox from current session."""
        if not self.session: return
        
        chunk_names = [f"Chunk {c.chunk_id} (Blocks {c.start_index}-{c.end_index})" for c in self.session.chunks]
        self.view.chunk_combo.config(values=chunk_names)
        
        if chunk_names:
            self.view.chunk_combo.current(0)
            self.on_chunk_selected(None)

    def on_chunk_size_changed(self, event):
        """Handle dynamic chunk resizing request."""
        if not self.session: return
        
        new_size = self.view.chunk_size_var.get()
        if new_size == self.session.max_blocks:
            return

        # 1. Pause Automation (Safety)
        was_polling = self.polling_active
        self.polling_active = False 
        
        # 2. Confirmation
        confirm = messagebox.askyesno(
            "Resize Session?", 
            f"Changing chunk size to {new_size} will reorganize your progress.\n\n"
            "This is a safe operation, but incomplete chunks will need review.\n\n"
            "Continue?"
        )
        
        if not confirm:
            # Revert UI selection
            self.view.chunk_size_var.set(self.session.max_blocks)
            self.polling_active = was_polling
            return
            
        # 3. Execute Transaction
        try:
            stats = self.session.rechunk_session(new_size)
            self.view.append_log(f"Rechunked to {new_size} blocks. Migrated: {stats['migrated']}, Pending: {stats['pending']}")
            
            # 4. Refresh UI
            self.refresh_chunk_combo()
            self.update_session_stats()
            
            # 5. Smart Navigation: Jump to first pending
            pending_chunk = self.session.get_next_pending_chunk()
            if pending_chunk:
                # Chunk IDs are 1-based, combo index is 0-based
                new_idx = pending_chunk.chunk_id - 1
                self.view.chunk_combo.current(new_idx)
                self.on_chunk_selected(None)
                self.view.append_log(f"Jumped to first pending chunk: {pending_chunk.chunk_id}")
            
            messagebox.showinfo("Resize Complete", f"Session resized successfully.\n{stats['migrated']} chunks preserved.")
            
        except Exception as e:
            messagebox.showerror("Resize Failed", f"Could not resize session: {e}")
            # Revert UI
            self.view.chunk_size_var.set(self.session.max_blocks)
        finally:
            # 6. Resume Automation
            if was_polling:
                self.polling_active = True
                self.root.after(100, self._poll_queue)

    def on_chunk_selected(self, event):
        if not self.session:
            return
            
        idx = self.view.chunk_combo.current()
        chunk = self.session.chunks[idx]
        
        # Update Original View
        self.view.txt_original.config(state=tk.NORMAL)
        self.view.txt_original.delete(1.0, tk.END)
        self.view.txt_original.insert(tk.END, "\n".join(chunk.extract_text()))
        self.view.txt_original.config(state=tk.DISABLED)
        
        # Set Translation Window
        self.view.txt_translation.delete(1.0, tk.END)
        existing_trans = self.session.completed_chunks.get(chunk.chunk_id)
        if existing_trans:
            self.view.txt_translation.insert(tk.END, "\n".join(existing_trans))
            self.view.append_log(f"Loaded saved progress for Chunk {chunk.chunk_id}")
            
        self.view.txt_translation.focus_set()
            
            
        self.validate_live()
        self.update_nav_buttons()

    def update_nav_buttons(self):
        if not self.session:
            return
            
        current_idx = self.view.chunk_combo.current()
        total_chunks = len(self.session.chunks)
        
        # Disable Prev if at start
        if current_idx <= 0:
            self.view.btn_prev_chunk.config(state=tk.DISABLED)
        else:
            self.view.btn_prev_chunk.config(state=tk.NORMAL)
            
        # Disable Next if at end
        if current_idx >= total_chunks - 1:
            self.view.btn_next_chunk.config(state=tk.DISABLED)
        else:
            self.view.btn_next_chunk.config(state=tk.NORMAL)

    def on_prev_chunk(self):
        if not self.session: return
        
        current_idx = self.view.chunk_combo.current()
        if current_idx > 0:
            self.view.chunk_combo.current(current_idx - 1)
            self.on_chunk_selected(None)

    def on_next_chunk(self):
        if not self.session: return
        
        # Validation Gate: Prevent moving forward if current chunk is invalid
        status_text = self.view.lbl_status.cget("text")
        if "FAILED" in status_text:
            messagebox.showwarning("Validation Failed", "Please fix errors in the current chunk before proceeding.")
            return

        current_idx = self.view.chunk_combo.current()
        if current_idx < len(self.session.chunks) - 1:
            self.view.chunk_combo.current(current_idx + 1)
            self.on_chunk_selected(None)
            
    def update_session_stats(self):
        if self.session:
            status = self.session.get_completion_status()
            self.view.lbl_chunk_info.config(text=status)
            
            if self.session.all_chunks_completed():
                self.view.btn_final_save.config(state=tk.NORMAL)
            else:
                self.view.btn_final_save.config(state=tk.DISABLED)

    def on_copy_all(self):
        if not self.session:
            return
        
        idx = self.view.chunk_combo.current()
        if idx < 0:
            return
        
        chunk = self.session.chunks[idx]
        
        # Use extract_text_with_signature for AI automation
        # This embeds the chunk signature for deterministic matching
        text = chunk.extract_text_with_signature()
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.view.append_log(f"Chunk {chunk.chunk_id} copied with embedded signature.")

    def on_paste_translation_clicked(self):
        try:
            content = self.root.clipboard_get()
        except tk.TclError:
            self.view.update_status("Clipboard is empty", "red")
            return

        self.view.txt_translation.delete(1.0, tk.END)
        self.view.txt_translation.insert(tk.END, content)

        self.validate_live()
        
        # Trigger Manual Automation if enabled (same as Ctrl+V)
        if self.view.automation_vars["full_auto"].get():
            self.root.after(200, self.trigger_manual_automation)

    def on_clipboard_paste(self, event):
        """Handle standard paste event to trigger manual automation."""
        # Allow the paste to happen first (let Tkinter handle insertion)
        # Then trigger automation after a short delay to ensure text is present
        self.view.append_log("DEBUG: Paste event detected. Scheduling check...")
        self.root.after(200, self.trigger_manual_automation)

    def on_text_edited(self, event):
        """Live evaluation on manual edit with debounce."""
        if hasattr(self, '_validation_timer'):
            self.root.after_cancel(self._validation_timer)
            
        def evaluate_and_maybe_auto_advance():
            self.validate_live()
            status_text = self.view.lbl_status.cget("text")
            if "PASSED" in status_text and self.view.automation_vars["full_auto"].get():
                self.trigger_manual_automation()
                
        self._validation_timer = self.root.after(500, evaluate_and_maybe_auto_advance)

    def trigger_manual_automation(self):
        """
        1. Check if Manual Automation is enabled.
        2. Validate.
        3. If Valid -> Save Chunk -> Check Completion -> Finalize -> Next File.
        """
        if not self.view.automation_vars["full_auto"].get():
            self.view.append_log("DEBUG: Manual Automation is DISABLED.")
            return # Feature disabled

        # 1. Validate
        self.validate_live()
        
        # 2. Check Status
        status_text = self.view.lbl_status.cget("text")
        self.view.append_log(f"DEBUG: Validation Status: {status_text}")
        
        if "PASSED" in status_text:
            self.view.append_log("Manual Auto: Validation PASSED. Auto-saving...")
            
            # 3. Auto-Save (which now also handles auto-advance and finalization)
            self.on_save_chunk_clicked()

    def load_next_file(self):
        """Find and load the next file in the listbox."""
        size = self.view.file_listbox.size()
        if size == 0: return

        # Get current selection index
        selection = self.view.file_listbox.curselection()
        if not selection:
            next_idx = 0 
        else:
            next_idx = selection[0] + 1
            
        if next_idx < size:
            # Select next file
            self.view.file_listbox.selection_clear(0, tk.END)
            self.view.file_listbox.selection_set(next_idx)
            self.view.file_listbox.activate(next_idx)
            self.view.file_listbox.see(next_idx)
            
            # Trigger load
            self.on_file_selected(None)
            self.view.append_log(f"Auto-loaded next file ({next_idx + 1}/{size}).")
        else:
            self.view.append_log("✓ All files in list processed.")
            messagebox.showinfo("Done", "All files in the list have been processed!")

    def validate_live(self):
        if not self.session:
            return
        
        idx = self.view.chunk_combo.current()
        if idx < 0: return
        chunk = self.session.chunks[idx]
        
        trans_content = self.view.txt_translation.get("1.0", "end-1c")
        if not trans_content:
            self.view.update_status("Waiting for input...", "black")
            self.view.btn_save_chunk.config(state=tk.DISABLED)
            return
            
        trans_lines = trans_content.splitlines()
        
        # Reuse domain validation logic
        errors = self.session.document.validate_translation(trans_lines)
        
        # Filter errors specific to this chunk's indices
        # validate_translation currently expects full document, but we want it per chunk
        # Requirement: "MUST reuse existing hierarchical validation"
        
        # Strategy: Mock a SubtitleDocument for just this chunk to reuse logic
        chunk_doc = SubtitleDocument(chunk.blocks)
        errors = chunk_doc.validate_translation(trans_lines)
        
        real_errors = [e for e in errors if "ERROR" in e]
        
        if real_errors:
            self.view.update_status(f"Validation FAILED: {real_errors[0]}", "red")
            self.view.btn_save_chunk.config(state=tk.DISABLED)
        else:
            self.view.update_status("Validation PASSED", "green")
            self.view.btn_save_chunk.config(state=tk.NORMAL)
            if errors: # warnings
                self.view.append_log(errors[0])

    def on_save_chunk_clicked(self):
        if not self.session:
            return
            
        idx = self.view.chunk_combo.current()
        chunk = self.session.chunks[idx]
        
        trans_content = self.view.txt_translation.get("1.0", "end-1c")
        trans_lines = trans_content.splitlines()
        
        self.session.mark_chunk_complete(chunk.chunk_id, trans_lines)
        self.view.append_log(f"Chunk {chunk.chunk_id} saved to session memory.")
        
        # Mark chunk as COMPLETED in SessionManager
        sm = session_manager.get_session_manager()
        if sm:
            sm.mark_chunk_completed(chunk.signature)
        
        self.update_session_stats()
        
        # If in Full Auto mode, clicking save manually should also advance
        if self.view.automation_vars.get("full_auto") and self.view.automation_vars["full_auto"].get():
            if self.session.all_chunks_completed():
                self.view.append_log("AI: ALL CHUNKS COMPLETED. Initiating auto-finalize...")
                self.root.after(500, self.on_final_save_clicked)
                self.root.after(1000, self.load_next_file)
            elif self.session:
                pending_chunk = self.session.get_next_pending_chunk()
                if pending_chunk:
                    target_idx = pending_chunk.chunk_id - 1
                    self.view.chunk_combo.current(target_idx)
                    self.on_chunk_selected(None)
                    self.view.append_log(f"Auto-moving to pending chunk: {pending_chunk.chunk_id}")

    def on_final_save_clicked(self):
        if not self.session or not self.session.all_chunks_completed():
            return
            
        try:
            full_trans_lines = self.session.collect_full_translation()
            new_content = self.session.document.inject_translation(full_trans_lines)
            
            atomic_save(self.current_file, new_content)
            messagebox.showinfo("Success", f"Full file saved successfully: {os.path.basename(self.current_file)}")
            self.view.append_log(f"FINAL SAVE SUCCESS: {self.current_file}")
            
            # Unset session to avoid accidental overwrites without reload
            self.on_file_selected(None)
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to perform final save: {e}")
            self.view.append_log(f"FINAL SAVE FAILED: {e}")

    # --- AI Automation Logic ---

    def toggle_automation(self):
        enabled = self.view.automation_vars["enabled"].get()
        full_auto = self.view.automation_vars["full_auto"].get()
        state = tk.NORMAL if enabled else tk.DISABLED
        
        self.view.start_auto_btn.config(state=state)
        self.view.start_ngrok_btn.config(state=state)
        self.view.stop_auto_btn.config(state=state)
        self.view.copy_url_btn.config(state=state)
        
        # In Full Auto mode, we freeze manual save buttons to prevent conflicts
        manual_state = tk.DISABLED if (enabled and full_auto) else tk.NORMAL
        self.view.btn_save_chunk.config(state=manual_state)
        self.view.btn_paste_translation.config(state=manual_state)
        # Note: btn_final_save is usually controlled by session status, 
        # but in full auto we keep it disabled for manual use.
        if enabled and full_auto:
            self.view.btn_final_save.config(state=tk.DISABLED)

        if enabled and not self.polling_active:
            local_translator.start_background_init()
            self.start_queue_polling()
        elif not enabled:
            self.polling_active = False

    def start_endpoint_server(self):
        if self.server_thread and self.server_thread.is_alive():
            self.view.append_log("Endpoint server is already running.")
            return

        self.view.append_log("Starting local endpoint server...")
        
        # 1. Resolve Port (Orchestrator Role)
        from integrations import config as integration_config
        try:
            self.running_port = endpoint_server.find_available_port(integration_config.ENDPOINT_PORT)
            self.view.append_log(f"Resolved available port: {self.running_port}")
        except Exception as e:
            self.view.append_log(f"CRITICAL: Could not find available port: {e}")
            return

        # 2. Start Server with Explicit Port
        self.server_thread = threading.Thread(
            target=endpoint_server.start_server, 
            args=(self.running_port,), 
            daemon=True
        )
        self.server_thread.start()
        
        self.view.automation_vars["status"].set("Starting...")
        self.view.start_ngrok_btn.config(state=tk.DISABLED) # Disable until ready

        # 3. Wait for readiness in background
        def check_ready():
            self.view.append_log("Waiting for server to initialize...")
            if ngrok_manager.wait_for_server(self.running_port, timeout=20):
                self.view.automation_vars["status"].set("Server Running")
                self.view.append_log(f"✓ Server is ready on localhost:{self.running_port}")
                self.view.start_ngrok_btn.config(state=tk.NORMAL)
            else:
                self.view.automation_vars["status"].set("Startup Failed")
                self.view.append_log("✗ CRITICAL: Server failed to start properly.")

        threading.Thread(target=check_ready, daemon=True).start()

    def start_ngrok(self):
        # check if server is running
        if not hasattr(self, 'running_port') or not self.running_port:
             self.view.append_log("Start the endpoint server first before enabling Ngrok.")
             return

        self.view.append_log(f"Initializing ngrok tunnel for port {self.running_port}...")
        self.view.update_status("Starting Ngrok...", "blue")

        def do_start():
            # Pass explicit port to ngrok manager
            # The manager will perform a readiness check (wait_for_server)
            max_retries = 2
            url = None
            
            for attempt in range(max_retries + 1):
                if attempt > 0:
                    self.view.append_log(f"Retry {attempt}/{max_retries} to start ngrok...")
                
                url = ngrok_manager.start_ngrok(self.running_port)
                if url:
                    break
                time.sleep(2)

            if url:
                self.view.automation_vars["url"].set(url)
                self.view.append_log(f"NGROK ACTIVE: {url}")
                self.view.update_status("Automation Ready", "green")
            else:
                self.view.append_log("CRITICAL: Ngrok failed after retries. Check .env or console.")
                self.view.update_status("Ngrok Failed", "red")

        threading.Thread(target=do_start, daemon=True).start()

    def stop_automation_layer(self):
        self.view.append_log("Stopping automation layer...")
        ngrok_manager.stop_ngrok()
        self.view.automation_vars["url"].set("Inactive")
        self.view.automation_vars["status"].set("Stopped")
        self.view.append_log("Ngrok tunnels closed.")

    def start_queue_polling(self):
        self.polling_active = True
        self.view.append_log("AI queue polling active.")
        self._poll_queue()

    def _poll_queue(self):
        if not self.polling_active:
            # We don't log here to avoid flooding, but the user should know polling is stopped
            return

        item = queue_handler.pop_translation()
        if item:
            translation = item['translation']
            raw_len = len(translation)
            
            self.view.append_log(f"AI: Processing incoming queue item (Size: {raw_len} chars)...")
            
            # Extract signature from the translated text
            signature, cleaned_translation = TranslationChunk.extract_signature_from_text(translation)
            
            if not signature:
                self.view.append_log(f"AI: ERROR - Signature missing in text. Snippet: '{translation[:50]}...'")
                self.view.append_log("TIP: The AI must include the '@@CHUNK_SIGNATURE=...@@' header.")
                return
            
            self.view.append_log(f"AI: Found signature '{signature}'. Matching with session...")
            
            if not self.session:
                self.view.append_log("AI: ERROR - No subtitle file is currently open in the editor.")
                return
            
            # Get SessionManager and attempt to acquire the chunk
            sm = session_manager.get_session_manager()
            if not sm:
                self.view.append_log("AI: ERROR - Session manager not found (App lifecycle error).")
                return
            
            # Find the target chunk by signature
            target_chunk = self.session.get_chunk_by_signature(signature)
            
            if not target_chunk:
                self.view.append_log(f"AI: ERROR - Signature '{signature}' does not match any chunk in the currently open file.")
                return
            
            # Acquire chunk for processing
            if not sm.acquire_chunk(signature):
                current_state = sm.get_chunk_state(signature)
                state_val = current_state.value if current_state else "UNKNOWN"
                self.view.append_log(f"AI: Warning - Chunk {target_chunk.chunk_id} is already in {state_val} state. Re-processing...")
                # We allow re-processing of PROCESSING/FAILED chunks for robustness
                # But we should be careful about COMPLETED. Let's allow it too if automation is on.
            
            try:
                chunk_id = target_chunk.chunk_id
                
                # 1. Update the UI selection to match the target chunk
                target_idx = chunk_id - 1
                self.view.chunk_combo.current(target_idx)
                
                # 2. Trigger standard chunk loading logic
                self.on_chunk_selected(None)
                
                # 3. Inject received translation (cleaned, without signature)
                self.view.txt_translation.delete(1.0, tk.END)
                self.view.txt_translation.insert(tk.END, cleaned_translation)
                
                # 4. Trigger validation
                self.validate_live()
                
                self.view.append_log(f"AI: Successfully injected translation for Chunk {chunk_id}.")
                
                # --- NEW: Automated Flow ---
                full_auto = self.view.automation_vars["full_auto"].get()
                if full_auto:
                    # Check validation status from the UI label
                    status_text = self.view.lbl_status.cget("text")
                    if "PASSED" in status_text:
                        self.view.append_log(f"AI: Validation PASSED. Auto-saving Chunk {chunk_id}...")
                        self.on_save_chunk_clicked()
                        
                        # Check if we should perform auto final save
                        if sm.can_initiate_final_save():
                            self.view.append_log("AI: ALL CHUNKS COMPLETED. Initiating auto-finalize...")
                            # Call final save on the next main thread loop for safety
                            self.root.after(500, self.on_final_save_clicked)
                    elif "FAILED" in status_text:
                        if "English characters" in status_text:
                            self.view.append_log(f"AI: English characters detected in Chunk {chunk_id}. Triggering offline auto-corrector...")
                            current_text = self.view.txt_translation.get("1.0", "end-1c")
                            
                            def try_auto_correct():
                                # Check if user changed selection while waiting
                                if self.view.chunk_combo.current() != target_idx:
                                    return
                                    
                                corrected_text = local_translator.auto_correct_english(current_text)
                                
                                if corrected_text == "NOT_READY":
                                    self.view.update_status("Initializing Translator (Please Wait)...", "orange")
                                    self.root.after(2000, try_auto_correct)
                                    return
                                    
                                if corrected_text != current_text:
                                    self.view.txt_translation.delete(1.0, tk.END)
                                    self.view.txt_translation.insert(tk.END, corrected_text)
                                    self.validate_live()
                                    new_status = self.view.lbl_status.cget("text")
                                    
                                    if "PASSED" in new_status:
                                        self.view.append_log(f"AI: Auto-correction successful! Saving Chunk {chunk_id}...")
                                        self.on_save_chunk_clicked()
                                        if sm.can_initiate_final_save():
                                            self.view.append_log("AI: ALL CHUNKS COMPLETED. Initiating auto-finalize...")
                                            self.root.after(500, self.on_final_save_clicked)
                                        return
                                
                                # If correction failed or wasn't enough
                                self.view.append_log(f"AI: Validation FAILED for Chunk {chunk_id}.")
                                chunk = self.session.chunks[target_idx]
                                text_to_copy = chunk.extract_text_with_signature()
                                self.root.clipboard_clear()
                                self.root.clipboard_append(text_to_copy)
                                self.view.append_log("AI: Invalid chunk auto-copied to clipboard for retry.")
                            
                            try_auto_correct()
                        else:
                            self.view.append_log(f"AI: Validation FAILED for Chunk {chunk_id}.")
                            
                            # AUTO-COPY Logic
                            chunk = self.session.chunks[target_idx]
                            text_to_copy = chunk.extract_text_with_signature()
                            self.root.clipboard_clear()
                            self.root.clipboard_append(text_to_copy)
                            self.view.append_log("AI: Invalid chunk auto-copied to clipboard for retry.")
                    else:
                        self.view.append_log(f"AI: Validation Status Unknown. Manual intervention required.")
                else:
                    self.view.append_log(f"NOTICE: Please review and click 'Save Chunk' manually.")
                
                # Note: Chunk state will be marked COMPLETED when user clicks Save (manually or via on_save_chunk_clicked)
            except Exception as e:
                self.view.append_log(f"AI: ERROR during injection: {e}")
                sm.mark_chunk_failed(signature)

        # Poll again in 500ms
        self.root.after(500, self._poll_queue)

    def copy_url_to_clipboard(self):
        url = self.view.automation_vars["url"].get()
        if url and url != "Inactive":
            self.root.clipboard_clear()
            self.root.clipboard_append(url)
            self.view.append_log("Ngrok URL copied to clipboard.")
        else:
            self.view.append_log("Nothing to copy.")
