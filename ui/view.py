import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox

class SubtitleUI(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.pack(fill=tk.BOTH, expand=True)
        
        # Main Paned Window
        self.paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left Panel: File Discovery & List
        self.sidebar = ttk.Frame(self.paned)
        self.paned.add(self.sidebar, weight=1)
        
        self.btn_select_dir = ttk.Button(self.sidebar, text="Scan Folder")
        self.btn_select_dir.pack(fill=tk.X, padx=5, pady=5)
        
        self.file_listbox = tk.Listbox(self.sidebar, selectmode=tk.SINGLE, font=("Segoe UI", 9))
        self.file_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Right Panel: Side-by-Side Viewers
        self.editor_paned = ttk.PanedWindow(self.paned, orient=tk.VERTICAL)
        self.paned.add(self.editor_paned, weight=4)
        
        # Chunk Selector Header
        self.chunk_frame = ttk.Frame(self.editor_paned)
        self.editor_paned.add(self.chunk_frame, weight=0)
        
        ttk.Label(self.chunk_frame, text="Select Chunk:").pack(side=tk.LEFT, padx=5)
        self.chunk_combo = ttk.Combobox(self.chunk_frame, state="readonly", width=30)
        self.chunk_combo.pack(side=tk.LEFT, padx=5, pady=5)
        
        self.lbl_chunk_info = ttk.Label(self.chunk_frame, text="0/0 chunks completed", font=("Segoe UI", 9, "italic"))
        self.lbl_chunk_info.pack(side=tk.LEFT, padx=10)

        # Top half: Original Text
        self.orig_frame = ttk.LabelFrame(self.editor_paned, text="Original Text (Read-Only)")
        self.editor_paned.add(self.orig_frame, weight=1)
        
        self.btn_copy_all = ttk.Button(self.orig_frame, text="Copy Current Chunk")
        self.btn_copy_all.pack(anchor=tk.E, padx=5, pady=2)
        
        self.txt_original = scrolledtext.ScrolledText(self.orig_frame, height=10, state=tk.DISABLED, bg="#f5f5f5")
        self.txt_original.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Bottom half: Translation Input
        self.trans_frame = ttk.LabelFrame(self.editor_paned, text="Translation Input (Paste Here)")
        self.editor_paned.add(self.trans_frame, weight=1)
        
        self.btn_paste_translation = ttk.Button(self.trans_frame, text="Paste Translation")
        self.btn_paste_translation.pack(anchor=tk.E, padx=5, pady=2)
        
        self.txt_translation = scrolledtext.ScrolledText(self.trans_frame, height=10)
        self.txt_translation.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # --- AI-Assisted Automation (Optional Layer) ---
        self.auto_frame = ttk.LabelFrame(self.editor_paned, text="AI-Assisted Automation (Optional)")
        self.editor_paned.add(self.auto_frame, weight=0)

        self.automation_vars = {
            "enabled": tk.BooleanVar(value=False),
            "url": tk.StringVar(value="Inactive"),
            "status": tk.StringVar(value="Stopped")
        }

        auto_toggle_frame = ttk.Frame(self.auto_frame)
        auto_toggle_frame.pack(fill=tk.X, padx=10, pady=5)

        self.auto_enable_check = ttk.Checkbutton(auto_toggle_frame, text="Enable AI Automation", variable=self.automation_vars["enabled"])
        self.auto_enable_check.pack(side=tk.LEFT)

        self.auto_controls_frame = ttk.Frame(self.auto_frame)
        self.auto_controls_frame.pack(fill=tk.X, padx=10, pady=5)

        self.start_auto_btn = ttk.Button(self.auto_controls_frame, text="1. Start Server")
        self.start_auto_btn.pack(side=tk.LEFT, padx=5)

        self.start_ngrok_btn = ttk.Button(self.auto_controls_frame, text="2. Start Ngrok")
        self.start_ngrok_btn.pack(side=tk.LEFT, padx=5)

        self.stop_auto_btn = ttk.Button(self.auto_controls_frame, text="Stop All")
        self.stop_auto_btn.pack(side=tk.LEFT, padx=5)

        ttk.Label(self.auto_controls_frame, text="Ngrok URL:").pack(side=tk.LEFT, padx=(15, 5))
        self.url_entry = ttk.Entry(self.auto_controls_frame, textvariable=self.automation_vars["url"], width=30, state="readonly")
        self.url_entry.pack(side=tk.LEFT, padx=5)

        self.copy_url_btn = ttk.Button(self.auto_controls_frame, text="Copy")
        self.copy_url_btn.pack(side=tk.LEFT, padx=5)
        
        # Footer: Status & Validation
        self.footer = ttk.Frame(self)
        self.footer.pack(fill=tk.X, padx=5, pady=5)
        
        self.btn_save_chunk = ttk.Button(self.footer, text="1. Save Chunk to Session", state=tk.DISABLED)
        self.btn_save_chunk.pack(side=tk.LEFT, padx=5)

        self.btn_final_save = ttk.Button(self.footer, text="2. Final Save to Disk", state=tk.DISABLED)
        self.btn_final_save.pack(side=tk.RIGHT, padx=5)
        
        self.lbl_status = ttk.Label(self.footer, text="Ready", font=("Segoe UI", 9, "bold"))
        self.lbl_status.pack(side=tk.LEFT, padx=20)
        
        self.log_area = scrolledtext.ScrolledText(self, height=5, state=tk.DISABLED, bg="black", fg="lime", font=("Consolas", 9))
        self.log_area.pack(fill=tk.X, padx=5, pady=5)

    def append_log(self, message):
        self.log_area.config(state=tk.NORMAL)
        self.log_area.insert(tk.END, f"> {message}\n")
        self.log_area.see(tk.END)
        self.log_area.config(state=tk.DISABLED)

    def update_status(self, text, color="black"):
        self.lbl_status.config(text=text, foreground=color)
