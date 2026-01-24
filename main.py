import tkinter as tk
from ui.view import SubtitleUI
from ui.logic import UILogic

def main():
    root = tk.Tk()
    root.title("Subtitle Validator & Management Suite")
    root.geometry("1100x800")
    
    view = SubtitleUI(root)
    logic = UILogic(view, root)
    
    root.mainloop()

if __name__ == "__main__":
    main()
