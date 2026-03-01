"""Shared utilities and base processor class for ISG."""

import subprocess
import threading
import queue


def check_ffmpeg():
    """Check if FFmpeg is available in the system PATH.
    
    Returns:
        bool: True if ffmpeg is found, False otherwise.
    """
    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        return True
    except FileNotFoundError:
        return False


class BaseProcessor:
    """Base class providing message queue communication for background tasks.
    
    All processors (encoder, decoder, youtube) inherit from this to get
    standardized logging, progress reporting, and error handling.
    """

    def __init__(self, message_queue: queue.Queue):
        self.message_queue = message_queue
        self.stop_event = threading.Event()

    def reset(self):
        """Reset stop_event before starting a new operation."""
        self.stop_event.clear()

    def log(self, message: str):
        """Send a log message to the UI."""
        self.message_queue.put(("log", message))

    def progress(self, value: float, message: str = None):
        """Report progress (0.0 to 1.0) with optional status message."""
        self.message_queue.put(("progress", (value, message)))

    def success(self, message: str):
        """Report successful completion."""
        self.message_queue.put(("success", message))

    def error(self, message: str):
        """Report an error."""
        self.message_queue.put(("error", message))

    def finished(self):
        """Signal that the operation has finished."""
        self.message_queue.put(("finished", None))

    def request_stop(self):
        """Request the current operation to stop."""
        self.stop_event.set()

    @property
    def should_stop(self) -> bool:
        """Check if a stop has been requested."""
        return self.stop_event.is_set()
