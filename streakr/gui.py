import os
import json
import datetime
import time
import threading
import tkinter as tk
from tkinter import PhotoImage, ttk, messagebox
from .activityMonitor import ActivityMonitor
from .utils import (load_config, save_config, load_streak_data, 
                   save_streak_data, get_active_windows, track_app_usage)

class StreakTrackerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Streakr")
        self.root.geometry("600x500")
        self.root.resizable(True, True)
        icon = PhotoImage(file="assets/icon.png")
        self.root.iconphoto(True, icon)
        
        self.config_file = "streak_config.json"
        self.data_file = "streak_data.json"
        self.config = load_config(self.config_file)
        self.streak_data = load_streak_data(self.data_file)
        
        # Initialize activity monitor with 2-minute timeout
        self.activity_monitor = ActivityMonitor(inactivity_timeout=120)
        
        self.running = False
        self.thread = None
        
        self._create_gui()
        self._populate_process_dropdown()
        self._update_display()

    def _create_gui(self):
        """Create the GUI components."""
        # Create notebook with tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create tabs
        self.track_frame = ttk.Frame(self.notebook)
        self.stats_frame = ttk.Frame(self.notebook)
        self.settings_frame = ttk.Frame(self.notebook)
        
        self.notebook.add(self.track_frame, text="Track Applications")
        self.notebook.add(self.stats_frame, text="Statistics")
        self.notebook.add(self.settings_frame, text="Settings")
        
        # Build tabs
        self._build_track_tab()
        self._build_stats_tab()
        self._build_settings_tab()
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        self.status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Control frame
        self.control_frame = ttk.Frame(self.root)
        self.control_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=5)
        
        self.tracking_status = tk.StringVar(value="Start Tracking")
        self.control_button = ttk.Button(self.control_frame, 
                                       textvariable=self.tracking_status,
                                       command=self._toggle_tracking)
        self.control_button.pack(side=tk.RIGHT)
        
        # Activity indicator
        self.activity_var = tk.StringVar(value="Activity: Not monitoring")
        self.activity_indicator = ttk.Label(self.control_frame, textvariable=self.activity_var)
        self.activity_indicator.pack(side=tk.LEFT)

    def _build_track_tab(self):
        """Build the Track tab UI."""
        # Frame for adding new applications
        add_frame = ttk.LabelFrame(self.track_frame, text="Add Application to Track")
        add_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Process selection
        ttk.Label(add_frame, text="Select Process:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.process_var = tk.StringVar()
        self.process_dropdown = ttk.Combobox(add_frame, textvariable=self.process_var, width=30)
        self.process_dropdown.grid(row=0, column=1, padx=5, pady=5)
        
        # Refresh button
        refresh_button = ttk.Button(add_frame, text="↻", width=3, command=self._populate_process_dropdown)
        refresh_button.grid(row=0, column=2, padx=5, pady=5)
        
        # Display name entry
        ttk.Label(add_frame, text="Display Name:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.display_name_var = tk.StringVar()
        display_name_entry = ttk.Entry(add_frame, textvariable=self.display_name_var, width=30)
        display_name_entry.grid(row=1, column=1, padx=5, pady=5, columnspan=2, sticky=tk.W+tk.E)
        
        # Minutes required entry
        ttk.Label(add_frame, text="Minutes Required:").grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        self.minutes_var = tk.StringVar(value="15")
        minutes_entry = ttk.Entry(add_frame, textvariable=self.minutes_var, width=10)
        minutes_entry.grid(row=2, column=1, padx=5, pady=5, sticky=tk.W)
        
        # Add button
        add_button = ttk.Button(add_frame, text="Add Application", command=self._add_application)
        add_button.grid(row=3, column=0, columnspan=3, padx=5, pady=10)
        
        # Frame for tracked applications
        tracked_frame = ttk.LabelFrame(self.track_frame, text="Tracked Applications")
        tracked_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create treeview
        columns = ("name", "process", "minutes", "actions")
        self.tracked_tree = ttk.Treeview(tracked_frame, columns=columns, show="headings", selectmode="browse")
        
        # Define headings
        self.tracked_tree.heading("name", text="Name")
        self.tracked_tree.heading("process", text="Process")
        self.tracked_tree.heading("minutes", text="Minutes Required")
        self.tracked_tree.heading("actions", text="Actions")
        
        # Define column widths
        self.tracked_tree.column("name", width=150)
        self.tracked_tree.column("process", width=150)
        self.tracked_tree.column("minutes", width=100)
        self.tracked_tree.column("actions", width=100)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(tracked_frame, orient=tk.VERTICAL, command=self.tracked_tree.yview)
        self.tracked_tree.configure(yscroll=scrollbar.set)
        
        # Pack treeview and scrollbar
        self.tracked_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind click handler
        self.tracked_tree.bind("<Button-1>", self._handle_tree_click)
        
        # Update tracked apps list
        self._update_tracked_apps()
    def _build_stats_tab(self):
        """Build the Stats tab UI."""
        # Create a frame for the stats
        stats_container = ttk.Frame(self.stats_frame)
        stats_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create a canvas with scrollbar
        canvas = tk.Canvas(stats_container)
        scrollbar = ttk.Scrollbar(stats_container, orient="vertical", command=canvas.yview)
        
        self.stats_content_frame = ttk.Frame(canvas)
        self.stats_content_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        
        canvas.create_window((0, 0), window=self.stats_content_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Pack the canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Add refresh button
        refresh_stats_button = ttk.Button(self.stats_frame, text="Refresh Stats", command=self._update_display)
        refresh_stats_button.pack(side=tk.BOTTOM, pady=10)

    def _build_settings_tab(self):
        """Build the Settings tab UI."""
        settings_frame = ttk.Frame(self.settings_frame, padding=10)
        settings_frame.pack(fill=tk.BOTH, expand=True)
        
        # Check interval setting
        ttk.Label(settings_frame, text="Check Interval (seconds):").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.check_interval_var = tk.StringVar(value=str(self.config["check_interval"]))
        check_interval_entry = ttk.Entry(settings_frame, textvariable=self.check_interval_var, width=10)
        check_interval_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        
        # Inactivity timeout setting
        ttk.Label(settings_frame, text="Inactivity Timeout (seconds):").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.inactivity_timeout_var = tk.StringVar(value=str(self.config.get("inactivity_timeout", 120)))
        inactivity_timeout_entry = ttk.Entry(settings_frame, textvariable=self.inactivity_timeout_var, width=10)
        inactivity_timeout_entry.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)
        
        # Settings explanation
        explanation = ttk.Label(settings_frame, text=(
            "Check Interval: How often to check if applications are running (in seconds).\n"
            "\n"
            "Inactivity Timeout: Time without keyboard or mouse activity before pausing tracking (in seconds)."
        ), wraplength=500, justify=tk.LEFT)
        explanation.grid(row=2, column=0, columnspan=2, padx=5, pady=10, sticky=tk.W)
        
        # Save settings button
        save_button = ttk.Button(settings_frame, text="Save Settings", command=self._save_settings)
        save_button.grid(row=3, column=0, columnspan=2, padx=5, pady=10)

    def _populate_process_dropdown(self):
        """Populate the process dropdown with active windows."""
        active_windows = get_active_windows()
        self.process_dropdown['values'] = active_windows
        
        def update_display_name(event):
            process = self.process_var.get()
            if process:
                base_name = os.path.splitext(process)[0]
                display_name = " ".join(word.capitalize() for word in base_name.split())
                self.display_name_var.set(display_name)
        
        self.process_dropdown.bind("<<ComboboxSelected>>", update_display_name)

    def _add_application(self):
        """Add a new application to track."""
        process = self.process_var.get()
        display_name = self.display_name_var.get()
        
        try:
            minutes = int(self.minutes_var.get())
            if minutes <= 0:
                raise ValueError("Minutes must be positive")
        except ValueError:
            messagebox.showerror("Invalid Input", "Minutes required must be a positive number.")
            return
        
        if not process or not display_name:
            messagebox.showerror("Missing Information", "Please fill in all fields.")
            return
        
        # Add to config
        self.config["applications"][process] = {
            "name": display_name,
            "min_minutes": minutes
        }
        save_config(self.config_file, self.config)
        
        # Initialize streak data
        if display_name not in self.streak_data:
            self.streak_data[display_name] = {
                "current_streak": 0,
                "longest_streak": 0,
                "last_used_date": None,
                "today_usage": 0,
                "streak_date": None
            }
            save_streak_data(self.data_file, self.streak_data)
        
        self._update_tracked_apps()
        
        # Clear form
        self.process_var.set("")
        self.display_name_var.set("")
        self.minutes_var.set("15")
        
        messagebox.showinfo("Success", f"Added {display_name} to tracked applications.")

    def _update_tracked_apps(self):
        """Update the list of tracked applications."""
        for item in self.tracked_tree.get_children():
            self.tracked_tree.delete(item)
        
        for process, app_info in self.config["applications"].items():
            self.tracked_tree.insert("", "end", values=(
                app_info["name"],
                process,
                app_info["min_minutes"],
                "Remove"
            ))

    def _handle_tree_click(self, event):
        """Handle clicks on the tracked applications tree."""
        region = self.tracked_tree.identify_region(event.x, event.y)
        if region == "cell":
            column = self.tracked_tree.identify_column(event.x)
            if column == "#4":  # Actions column
                item = self.tracked_tree.identify_row(event.y)
                if item:
                    values = self.tracked_tree.item(item, "values")
                    if values:
                        self._remove_application(values[1])  # Process name

    def _remove_application(self, process_name):
        """Remove an application from tracking."""
        if messagebox.askyesno("Confirm Deletion", "Are you sure you want to remove this application?"):
            display_name = self.config["applications"][process_name]["name"]
            
            del self.config["applications"][process_name]
            save_config(self.config_file, self.config)
            
            if display_name in self.streak_data:
                del self.streak_data[display_name]
                save_streak_data(self.data_file, self.streak_data)
            
            self._update_tracked_apps()
            self._update_display()

    def _toggle_tracking(self):
        """Start or stop tracking."""
        if not self.running:
            if not self.config["applications"]:
                messagebox.showwarning("No Applications", "Please add at least one application to track.")
                return
            
            self.running = True
            self.tracking_status.set("Stop Tracking")
            self.activity_monitor.start()
            
            self.thread = threading.Thread(target=self._tracking_loop, daemon=True)
            self.thread.start()
            
            self.status_var.set("Tracking active")
        else:
            self.running = False
            self.tracking_status.set("Start Tracking")
            self.activity_monitor.stop()
            if self.thread:
                self.thread.join(timeout=1.0)
            self.status_var.set("Tracking stopped")

    def _update_activity_indicator(self):
        """Update the activity indicator."""
        if not self.running:
            self.activity_var.set("Activity: Not monitoring")
        elif self.activity_monitor.is_active:
            self.activity_var.set("Activity: Active ✓")
        else:
            self.activity_var.set("Activity: Inactive ✗")

    def _tracking_loop(self):
        """Main tracking loop."""
        while self.running:
            try:
                self.root.after(0, self._update_activity_indicator)
                
                if self.activity_monitor.is_active:
                    for process_name in list(self.config["applications"].keys()):
                        track_app_usage(process_name, self.config, self.streak_data, self.activity_monitor)
                    save_streak_data(self.data_file, self.streak_data)
                    self.root.after(0, self._update_display)
                
                time.sleep(self.config["check_interval"])
                
                # Sleep for check interval
                # for _ in range(self.config["check_interval"]):
                #     if not self.running:
                #         break
                #     time.sleep(1)
            except Exception as e:
                # print(f"Error in tracking loop: {e}")
                # self.status_var.set(f"Error: {str(e)}")
                # self.running = False
                # self.tracking_status.set("Start Tracking")
                self.root.after(0, lambda: self.status_var.set(f"Error: {str(e)}"))
                self.running = False
                self.root.after(0, lambda: self.tracking_status.set("Start Tracking"))
                break

    def _update_display(self):
        """Update the statistics display."""
        # Clear existing widgets
        for widget in self.stats_content_frame.winfo_children():
            widget.destroy()
        
        # Current date
        date_label = ttk.Label(self.stats_content_frame, 
                              text=f"Date: {datetime.date.today().strftime('%Y-%m-%d')}",
                              font=("Arial", 12, "bold"))
        date_label.pack(anchor=tk.W, padx=10, pady=(10, 20))
        
        # Display stats for each application
        for app_name, data in self.streak_data.items():
            # Find the min_minutes for this app
            min_minutes = 0
            for process_name, app_info in self.config["applications"].items():
                if app_info["name"] == app_name:
                    min_minutes = app_info["min_minutes"]
                    break
            
            # Skip if app is no longer being tracked
            if min_minutes == 0:
                continue
            
            # Create a frame for this app
            app_frame = ttk.LabelFrame(self.stats_content_frame, text=app_name)
            app_frame.pack(fill=tk.X, expand=True, padx=10, pady=5)
            
            # Current streak
            current_streak = data.get("current_streak", 0)
            ttk.Label(app_frame, text=f"Current Streak: {current_streak} days").pack(anchor=tk.W, padx=10, pady=2)
            
            # Longest streak
            longest_streak = data.get("longest_streak", 0)
            ttk.Label(app_frame, text=f"Longest Streak: {longest_streak} days").pack(anchor=tk.W, padx=10, pady=2)
            
            # Today's usage
            today_usage = round(data.get("today_usage", 0), 1)
            
            # Progress bar for today's usage
            progress_frame = ttk.Frame(app_frame)
            progress_frame.pack(fill=tk.X, padx=10, pady=5)
            
            ttk.Label(progress_frame, text=f"Today's Usage: {today_usage}/{min_minutes} minutes").pack(side=tk.LEFT)
            
            # Calculate progress percentage (capped at 100%)
            progress_pct = min(100, (today_usage / min_minutes) * 100)
            
            # Status indicator
            if today_usage >= min_minutes:
                status_label = ttk.Label(progress_frame, text="✓", foreground="green")
            else:
                status_label = ttk.Label(progress_frame, text="...", foreground="orange")
            status_label.pack(side=tk.RIGHT)
            
            # Progress bar
            progress_bar = ttk.Progressbar(app_frame, orient=tk.HORIZONTAL, length=200, mode='determinate')
            progress_bar["value"] = progress_pct
            progress_bar.pack(fill=tk.X, padx=10, pady=(0, 10))
            
            # Last streak update
            if data.get("streak_date"):
                streak_date = datetime.date.fromisoformat(data["streak_date"])
                ttk.Label(app_frame, 
                         text=f"Last streak update: {streak_date.strftime('%Y-%m-%d')}",
                         font=("Arial", 8)).pack(anchor=tk.E, padx=10, pady=(0, 5))

    def _save_settings(self):
        """Save settings from the settings tab."""
        try:
            check_interval = int(self.check_interval_var.get())
            inactivity_timeout = int(self.inactivity_timeout_var.get())
            
            if check_interval < 1 or inactivity_timeout < 1:
                raise ValueError("Values must be at least 1 second")
            
            self.config["check_interval"] = check_interval
            self.config["inactivity_timeout"] = inactivity_timeout
            save_config(self.config_file, self.config)
            
            self.activity_monitor.inactivity_timeout = inactivity_timeout
            
            messagebox.showinfo("Settings Saved", "Settings have been saved successfully.")
        except ValueError as e:
            messagebox.showerror("Invalid Input", str(e))
