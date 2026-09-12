import os

def shutdown_system(delay: int = 60) -> str:
    """
    Schedules a system shutdown in `delay` seconds.
    """
    try:
        os.system(f"shutdown /s /t {delay}")
        return f"System will shut down in {delay} seconds."
    except Exception as e:
        return f"Failed to execute shutdown: {str(e)}"

def cancel_shutdown() -> str:
    """
    Cancels a scheduled system shutdown.
    """
    try:
        os.system("shutdown /a")
        return "System shutdown canceled."
    except Exception as e:
        return f"Failed to cancel shutdown: {str(e)}"
