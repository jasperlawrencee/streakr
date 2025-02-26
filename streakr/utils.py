import platform
from AppKit import NSWorkspace

def getOS():
    osName = platform.system()
    
    if osName == "Darwin":
        return "macOS"
    elif osName == "Windows":
        return "windows"
    elif osName == "Linux":
        return "linux"
    else:
        return "unknown"

def getAllWindows():
    getWindows = [apps["NSApplicationName"] for apps in NSWorkspace.sharedWorkspace().launchedApplications()]

    # return conditional os window grabber method
    return getWindows