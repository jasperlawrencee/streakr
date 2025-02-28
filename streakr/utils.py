import os
import json
import psutil
import sys
import datetime
from Quartz import (CGWindowListCopyWindowInfo, kCGWindowListOptionOnScreenOnly, 
                   kCGNullWindowID, kCGWindowOwnerName)

def load_config(config_file):
    """Load configuration or create default if it doesn't exist."""
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            return json.load(f)
    else:
        default_config = {
            "applications": {},
            "check_interval": 60,
            "inactivity_timeout": 120
        }
        with open(config_file, 'w') as f:
            json.dump(default_config, f, indent=4)
        return default_config

def save_config(config_file, config):
    """Save config to file."""
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=4)

def load_streak_data(data_file):
    """Load streak data or create default if it doesn't exist."""
    if os.path.exists(data_file):
        with open(data_file, 'r') as f:
            return json.load(f)
    else:
        default_data = {}
        with open(data_file, 'w') as f:
            json.dump(default_data, f, indent=4)
        return default_data

def save_streak_data(data_file, streak_data):
    """Save streak data to file."""
    with open(data_file, 'w') as f:
        json.dump(streak_data, f, indent=4)

def get_active_windows():
    """Get list of active windows based on platform."""
    active_windows = []
    if sys.platform == "darwin":  # macOS
        try:
            window_list = CGWindowListCopyWindowInfo(kCGWindowListOptionOnScreenOnly, 
                                                   kCGNullWindowID)
            for window in window_list:
                try:
                    app_name = window.get(kCGWindowOwnerName, "")
                    if app_name and app_name not in active_windows:
                        active_windows.append(app_name)
                except:
                    continue
        except ImportError:
            print("Please install pyobjc-framework-Quartz for window detection on macOS")
            
    elif sys.platform == "win32":  # Windows
        try:
            import win32gui
            import win32process
            
            def callback(hwnd, windows):
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd)
                    if title and not title.isspace():
                        try:
                            _, pid = win32process.GetWindowThreadProcessId(hwnd)
                            process = psutil.Process(pid)
                            app_name = process.name()
                            if app_name and app_name not in windows:
                                windows.append(app_name)
                        except:
                            pass
            
            win32gui.EnumWindows(callback, active_windows)
            
        except ImportError:
            print("Please install pywin32 for window detection on Windows")
            
    else:  # Linux
        try:
            import Xlib
            import Xlib.display
            
            display = Xlib.display.Display()
            root = display.screen().root
            
            window_ids = root.get_full_property(
                display.intern_atom('_NET_CLIENT_LIST'),
                Xlib.X.AnyPropertyType
            ).value
            
            for window_id in window_ids:
                window = display.create_resource_object('window', window_id)
                try:
                    wmname = window.get_wm_name()
                    wmclass = window.get_wm_class()
                    if wmclass and wmclass[1] not in active_windows:
                        active_windows.append(wmclass[1])
                except:
                    continue
                    
        except ImportError:
            print("Please install python-xlib for window detection on Linux")
    
    return sorted(active_windows)

def track_app_usage(process_name, config, streak_data, activity_monitor):
    """Track the usage time of a specific application."""
    app_config = config["applications"].get(process_name)
    if not app_config:
        return
    
    app_name = app_config["name"]
    min_minutes = app_config["min_minutes"]
    today = datetime.date.today().isoformat()
    
    # Initialize app entry in streak_data if it doesn't exist
    if app_name not in streak_data:
        streak_data[app_name] = {
            "current_streak": 0,
            "longest_streak": 0,
            "last_used_date": None,
            "today_usage": 0,
            "streak_date": None
        }
    
    # Initialize or reset today's usage if it's a new day
    if streak_data[app_name].get("last_used_date") != today:
        streak_data[app_name]["today_usage"] = 0
    
    # Check if the app is running
    is_running = False
    for proc in psutil.process_iter(['name']):
        if proc.info['name'] == process_name:
            is_running = True
            break
    
    # Update usage time only if app is running AND user is active
    if is_running and activity_monitor.is_active:
        # Add the time since last check (in minutes)
        streak_data[app_name]["today_usage"] += config["check_interval"] / 60
        streak_data[app_name]["last_used_date"] = today
        
        # Check if the minimum usage time has been met for today
        if streak_data[app_name]["today_usage"] >= min_minutes:
            if streak_data[app_name].get("streak_date") != today:
                streak_data[app_name]["current_streak"] += 1
                streak_data[app_name]["streak_date"] = today
                if streak_data[app_name]["current_streak"] > streak_data[app_name]["longest_streak"]:
                    streak_data[app_name]["longest_streak"] = streak_data[app_name]["current_streak"]
    
    # Check for broken streaks (if last use was more than 1 day ago)
    if streak_data[app_name].get("last_used_date"):
        last_date = datetime.date.fromisoformat(streak_data[app_name]["last_used_date"])
        today_date = datetime.date.today()
        days_since_last_use = (today_date - last_date).days
        
        if days_since_last_use > 1:  # If more than 1 day has passed
            streak_data[app_name]["current_streak"] = 0
