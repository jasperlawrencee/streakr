import tkinter as tk
from streakr.gui import StreakTrackerGUI

def main():
    root = tk.Tk()
    app = StreakTrackerGUI(root)
    
    def on_closing():
        if app.running:
            app.running = False
            app.activity_monitor.stop()
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()
