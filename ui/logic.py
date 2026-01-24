import os
import queue
import threading
import time
import tkinter as tk
from integrations import endpoint_server, ngrok_manager, queue_handler
from tkinter import filedialog, messagebox
from core.file_ops import scan_directory_threaded, atomic_save
from core.vtt_converter import normalize_file
from core.domain import SubtitleDocument
from core.session import TranslationSession

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
        self.view.btn_paste_translation.config(command=self.on_paste_translation_clicked)
        
        # Bind Automation events
        self.view.auto_enable_check.config(command=self.toggle_automation)
        self.view.start_auto_btn.config(command=self.start_endpoint_server)
        self.view.start_ngrok_btn.config(command=self.start_ngrok)
        self.view.stop_auto_btn.config(command=self.stop_automation_layer)
        self.view.copy_url_btn.config(command=self.copy_url_to_clipboard)
        
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
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            doc = SubtitleDocument.from_srt(content)
            self.file_map[file_path] = doc
            
            # Initialize Session
            self.session = TranslationSession(doc)
            
            # Update Chunk Selector
            chunk_names = [f"Chunk {c.chunk_id} (Blocks {c.start_index}-{c.end_index})" for c in self.session.chunks]
            self.view.chunk_combo.config(values=chunk_names)
            
            if chunk_names:
                self.view.chunk_combo.current(0)
                self.on_chunk_selected(None)
            
            self.view.update_status(f"Loaded {os.path.basename(file_path)}", "black")
            self.update_session_stats()
            
        except Exception as e:
            messagebox.showerror("Parse Error", f"Could not parse file: {e}")

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

    def update_session_stats(self):
        if self.session:
            status = self.session.get_completion_status()
            self.view.lbl_chunk_info.config(text=status)
            
            if self.session.all_chunks_completed():
                self.view.btn_final_save.config(state=tk.NORMAL)
            else:
                self.view.btn_final_save.config(state=tk.DISABLED)

    def on_copy_all(self):
        text = self.view.txt_original.get(1.0, tk.END)
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.view.append_log("Current chunk text copied to clipboard.")

    def on_paste_translation_clicked(self):
        try:
            content = self.root.clipboard_get()
        except tk.TclError:
            self.view.update_status("Clipboard is empty", "red")
            return

        self.view.txt_translation.delete(1.0, tk.END)
        self.view.txt_translation.insert(tk.END, content)

        self.validate_live()

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
        # Let's check block count and ID ranges manually or update domain?
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
        self.update_session_stats()

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
            self.view.append_log("Endpoint server is already running.")
            return

        self.view.append_log("Starting local endpoint server...")
        self.server_thread = threading.Thread(target=endpoint_server.start_server, daemon=True)
        self.server_thread.start()
        self.view.automation_vars["status"].set("Server Running")
        self.view.append_log("Endpoint server started on localhost:8765")

    def start_ngrok(self):
        self.view.append_log("Initializing ngrok tunnel...")
        def do_start():
            url = ngrok_manager.start_ngrok()
            if url:
                self.view.automation_vars["url"].set(url)
                self.view.append_log(f"NGROK ACTIVE: {url}")
                self.view.update_status("Automation Ready", "green")
            else:
                self.view.append_log("CRITICAL: Ngrok failed. Check .env for NGROK_AUTHTOKEN.")
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
            return

        item = queue_handler.pop_translation()
        if item:
            chunk_id = item['chunk_id']
            translation = item['translation']
            
            self.view.append_log(f"AI: Received translation for Chunk {chunk_id}")
            
            # Auto-inject if the current selected chunk matches
            if self.session:
                current_idx = self.view.chunk_combo.current()
                if current_idx >= 0:
                    current_chunk = self.session.chunks[current_idx]
                    if current_chunk.chunk_id == chunk_id:
                        self.view.txt_translation.delete(1.0, tk.END)
                        self.view.txt_translation.insert(tk.END, translation)
                        self.validate_live()
                        self.view.append_log(f"AI: Injected translation into editor for Chunk {chunk_id}")
                    else:
                        # Store it in session even if not selected? 
                        # Requirement: "Trigger existing live validation logic"
                        # For safety, we only inject into the ACTIVE editor.
                        # But we could also just mark it complete if we were bold.
                        # Let's stick to safety: inject ONLY into active chunk.
                        self.view.append_log(f"AI: Chunk {chunk_id} received but not currently selected. Ignoring injection.")
            else:
                self.view.append_log("AI: No active session. Ignoring received translation.")

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
