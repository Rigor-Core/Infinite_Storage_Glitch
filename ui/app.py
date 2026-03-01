"""Main application window for Infinite Storage Glitch.

Assembles all UI tabs, manages the message queue for background tasks,
and displays the "Rigor Core" watermark.
"""

import queue

import customtkinter as ctk
from tkinter import messagebox

from core.encoder import Encoder
from core.decoder import Decoder
from ui.tabs.encode_tab import EncodeTab
from ui.tabs.decode_tab import DecodeTab

# Appearance configuration
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class App(ctk.CTk):
    """Main application window for ISG."""

    def __init__(self):
        super().__init__()
        self.title("ISG - Infinite Storage Glitch")
        self.geometry("900x650")

        # Grid configuration
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)  # Tabview (expandable)
        self.grid_rowconfigure(1, weight=0)  # Status label
        self.grid_rowconfigure(2, weight=0)  # Progress bar
        self.grid_rowconfigure(3, weight=0)  # Log
        self.grid_rowconfigure(4, weight=0)  # Watermark

        # Message queue for background task communication
        self._queue = queue.Queue()

        # Core processors
        self._encoder = Encoder(self._queue)
        self._decoder = Decoder(self._queue)

        # Build the UI
        self._build_tabs()
        self._build_status_bar()
        self._build_watermark()

        # Start message queue polling
        self.after(100, self._check_queue)

    def _build_tabs(self):
        """Create the tabview and add all tabs."""
        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=0, column=0, padx=20, pady=(10, 0), sticky="nsew")

        tab_encode = self.tabview.add("Codificar")
        tab_decode = self.tabview.add("Decodificar")

        # Encode Tab
        self.encode_tab = EncodeTab(
            tab_encode, self._encoder, lambda: self.progress_bar
        )
        self.encode_tab.pack(fill="both", expand=True)

        # Decode Tab
        self.decode_tab = DecodeTab(
            tab_decode, self._decoder, lambda: self.progress_bar
        )
        self.decode_tab.pack(fill="both", expand=True)

    def _build_status_bar(self):
        """Create the status label, progress bar, and log textbox."""
        self.status_label = ctk.CTkLabel(self, text="Listo", text_color="gray")
        self.status_label.grid(row=1, column=0, sticky="w", padx=25)

        self.progress_bar = ctk.CTkProgressBar(self)
        self.progress_bar.grid(row=2, column=0, padx=20, pady=(0, 10), sticky="ew")
        self.progress_bar.set(0)

        self.log_box = ctk.CTkTextbox(
            self,
            height=120,
            font=("Consolas", 12),
            fg_color="#1a1a1a",
            text_color="#00ff00",
        )
        self.log_box.grid(row=3, column=0, padx=20, pady=(0, 5), sticky="ew")

    def _build_watermark(self):
        """Add the 'Rigor Core' watermark in the bottom-left corner."""
        watermark = ctk.CTkLabel(
            self,
            text="Rigor Core",
            font=("Arial", 10),
            text_color="#B0B0B0",
            anchor="w",
        )
        watermark.grid(row=4, column=0, sticky="w", padx=20, pady=(0, 8))

    def _set_ui_state(self, disabled: bool):
        """Enable or disable all action buttons across tabs."""
        state = "disabled" if disabled else "normal"
        self.encode_tab.set_state(state)
        self.decode_tab.set_state(state)

    def _check_queue(self):
        """Poll the message queue and update the UI accordingly."""
        try:
            while True:
                msg_type, data = self._queue.get_nowait()

                if msg_type == "log":
                    self.log_box.insert("end", f"> {data}\n")
                    self.log_box.see("end")

                elif msg_type == "progress":
                    value, msg = data
                    self.progress_bar.stop()
                    self.progress_bar.set(value)
                    if msg:
                        self.status_label.configure(text=msg)

                elif msg_type == "success":
                    messagebox.showinfo("Éxito", data)
                    self.progress_bar.stop()
                    self.progress_bar.set(1)
                    self.status_label.configure(text="Completado")
                    self._set_ui_state(False)

                elif msg_type == "error":
                    messagebox.showerror("Error", data)
                    self.progress_bar.stop()
                    self.progress_bar.set(0)
                    self.status_label.configure(text="Error")
                    self._set_ui_state(False)

                elif msg_type == "finished":
                    self.progress_bar.stop()
                    self._set_ui_state(False)
                    self.status_label.configure(text="Listo")

        except queue.Empty:
            pass

        self.after(100, self._check_queue)
