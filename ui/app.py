import tkinter as tk
from .views import MainView
from .controllers import PipelineController
from . import utils

class SubtitleApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Subtitle Translation Manager - Professional Suite")
        self.root.geometry("900x700")
        self.root.minsize(800, 600)
        
        # Initialize View
        self.view = MainView(self.root)
        
        # Initialize Controller
        self.controller = PipelineController(self.view)
        
        # Link Controller to View
        self.view.set_controller(self.controller)
        
        # Initial Refresh
        self.controller.refresh_dashboard()
        self.controller.log("Application started. Ready to manage workflow.")

def main():
    root = tk.Tk()
    app = SubtitleApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
