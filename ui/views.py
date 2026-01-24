import tkinter as tk
from tkinter import ttk, scrolledtext

class MainView(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.build_ui()

    def build_ui(self):
        # 1. Project Dashboard (Stats)
        stats_frame = ttk.LabelFrame(self, text="Project Dashboard")
        stats_frame.pack(fill=tk.X, pady=5)
        
        self.stat_vars = {
            "srt_count": tk.StringVar(value="0"),
            "chunk_count": tk.StringVar(value="0"),
            "done_count": tk.StringVar(value="0"),
            "pending_count": tk.StringVar(value="0")
        }
        
        self.automation_vars = {
            "enabled": tk.BooleanVar(value=False),
            "url": tk.StringVar(value="Inactive"),
            "status": tk.StringVar(value="Stopped")
        }
        
        labels = [
            ("Original SRTs:", "srt_count"),
            ("Total Chunks:", "chunk_count"),
            ("Go Outputs:", "done_count"),
            ("Pending Chunks:", "pending_count")
        ]
        
        for i, (text, var_name) in enumerate(labels):
            tk.Label(stats_frame, text=text).grid(row=0, column=i*2, padx=5, pady=5, sticky=tk.W)
            tk.Label(stats_frame, textvariable=self.stat_vars[var_name], font=("Courier", 10, "bold")).grid(row=0, column=i*2+1, padx=5, pady=5, sticky=tk.W)

        self.refresh_btn = ttk.Button(stats_frame, text="Refresh Status")
        self.refresh_btn.grid(row=0, column=8, padx=10, pady=5)

        # 2. Actions & Pending Viewer (Paned Window)
        middle_pane = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        middle_pane.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Actions Panel
        actions_frame = ttk.LabelFrame(middle_pane, text="Actions")
        middle_pane.add(actions_frame, weight=1)
        
        self.split_btn = ttk.Button(actions_frame, text="1. Split SRT Files")
        self.split_btn.pack(fill=tk.X, padx=10, pady=10)
        
        self.status_btn = ttk.Button(actions_frame, text="2. Check Pending Status")
        self.status_btn.pack(fill=tk.X, padx=10, pady=10)
        
        self.consistency_btn = ttk.Button(actions_frame, text="3. Check Consistency")
        self.consistency_btn.pack(fill=tk.X, padx=10, pady=10)
        
        self.merge_btn = ttk.Button(actions_frame, text="4. Merge Final Subtitles")
        self.merge_btn.pack(fill=tk.X, padx=10, pady=10)

        self.export_btn = ttk.Button(actions_frame, text="5. Export Final to VTT")
        self.export_btn.pack(fill=tk.X, padx=10, pady=10)
        
        # Pending Viewer
        pending_frame = ttk.LabelFrame(middle_pane, text="Pending Chunks")
        middle_pane.add(pending_frame, weight=2)
        
        self.pending_text = scrolledtext.ScrolledText(pending_frame, height=10, width=40, state=tk.DISABLED, bg="#f0f0f0")
        self.pending_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 3. AI-Assisted Automation (Optional Layer)
        self.auto_frame = ttk.LabelFrame(self, text="AI-Assisted Automation (Optional)")
        self.auto_frame.pack(fill=tk.X, pady=5)

        auto_toggle_frame = ttk.Frame(self.auto_frame)
        auto_toggle_frame.pack(fill=tk.X, padx=10, pady=5)

        self.auto_enable_check = ttk.Checkbutton(auto_toggle_frame, text="Enable AI Automation Mode", variable=self.automation_vars["enabled"])
        self.auto_enable_check.pack(side=tk.LEFT)

        self.auto_controls_frame = ttk.Frame(self.auto_frame)
        self.auto_controls_frame.pack(fill=tk.X, padx=10, pady=5)

        self.start_auto_btn = ttk.Button(self.auto_controls_frame, text="Start Endpoint Server")
        self.start_auto_btn.pack(side=tk.LEFT, padx=5)

        self.start_ngrok_btn = ttk.Button(self.auto_controls_frame, text="Start Ngrok Tunnel")
        self.start_ngrok_btn.pack(side=tk.LEFT, padx=5)

        self.stop_auto_btn = ttk.Button(self.auto_controls_frame, text="Stop All")
        self.stop_auto_btn.pack(side=tk.LEFT, padx=5)

        ttk.Label(self.auto_controls_frame, text="Public URL:").pack(side=tk.LEFT, padx=(15, 5))
        self.url_entry = ttk.Entry(self.auto_controls_frame, textvariable=self.automation_vars["url"], width=40, state="readonly")
        self.url_entry.pack(side=tk.LEFT, padx=5)

        self.copy_url_btn = ttk.Button(self.auto_controls_frame, text="Copy URL")
        self.copy_url_btn.pack(side=tk.LEFT, padx=5)

        # 3. Log Viewer
        log_frame = ttk.LabelFrame(self, text="Execution Logs")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=8, state=tk.DISABLED, bg="black", fg="lime", font=("Consolas", 9))
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def update_stats(self, stats):
        for key, value in stats.items():
            if key in self.stat_vars:
                self.stat_vars[key].set(str(value))

    def append_log(self, message):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def update_pending_text(self, text):
        self.pending_text.config(state=tk.NORMAL)
        self.pending_text.delete(1.0, tk.END)
        self.pending_text.insert(tk.END, text)
        self.pending_text.config(state=tk.DISABLED)

    def set_controller(self, controller):
        self.refresh_btn.config(command=controller.refresh_dashboard)
        self.split_btn.config(command=controller.run_split)
        self.status_btn.config(command=controller.run_status)
        self.consistency_btn.config(command=controller.run_consistency)
        self.merge_btn.config(command=controller.run_merge)
        self.export_btn.config(command=controller.run_export_vtt)
        
        # Automation commands
        self.auto_enable_check.config(command=lambda: controller.toggle_automation(self.automation_vars["enabled"].get()))
        self.start_auto_btn.config(command=controller.start_endpoint_server)
        self.start_ngrok_btn.config(command=controller.start_ngrok)
        self.stop_auto_btn.config(command=controller.stop_automation_layer)
        self.copy_url_btn.config(command=lambda: controller.copy_to_clipboard(self.automation_vars["url"].get()))

        # Initial state
        controller.toggle_automation(False)
