import time
import threading
from pynput import mouse, keyboard

class ActivityMonitor:
    """Monitors keyboard and mouse activity."""
    def __init__(self, inactivity_timeout=60):  # Default 60 seconds timeout
        self.inactivity_timeout = inactivity_timeout
        self.last_activity = time.time()
        self.is_active = True
        self.running = False
        self.monitor_thread = None
        
        # Setup listeners
        self.mouse_listener = mouse.Listener(on_move=self._on_activity, 
                                            on_click=self._on_activity, 
                                            on_scroll=self._on_activity)
        self.keyboard_listener = keyboard.Listener(on_press=self._on_activity)
    
    def _on_activity(self, *args, **kwargs):
        """Called when activity is detected."""
        self.last_activity = time.time()
        print("activity detected")
        if not self.is_active:
            self.is_active = True
    
    def start(self):
        """Start monitoring activity."""
        if self.running:
            return
            
        self.running = True
        self.last_activity = time.time()
        self.is_active = True
        
        # Start listeners
        self.mouse_listener.start()
        self.keyboard_listener.start()
        
        # Start monitor thread
        self.monitor_thread = threading.Thread(target=self._monitor_activity, daemon=True)
        self.monitor_thread.start()
    
    def stop(self):
        """Stop monitoring activity."""
        self.running = False
        
        # Stop listeners
        if self.mouse_listener.is_alive():
            self.mouse_listener.stop()
        if self.keyboard_listener.is_alive():
            self.keyboard_listener.stop()
            
        # Create new listeners for next time
        self.mouse_listener = mouse.Listener(on_move=self._on_activity, 
                                            on_click=self._on_activity, 
                                            on_scroll=self._on_activity)
        self.keyboard_listener = keyboard.Listener(on_press=self._on_activity)
    
    def _monitor_activity(self):
        """Thread to monitor for inactivity."""
        while self.running:
            # Check if inactive
            if time.time() - self.last_activity > self.inactivity_timeout:
                if self.is_active:
                    self.is_active = False
            
            # Wait a bit before checking again
            time.sleep(1)
