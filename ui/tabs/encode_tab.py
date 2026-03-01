"""Encode tab UI component.

Provides the interface for selecting a file, choosing an encoder,
and starting the file-to-video encoding process.
"""

import os
import threading

import customtkinter as ctk
from tkinter import filedialog, messagebox


class EncodeTab(ctk.CTkFrame):
    """Tab for encoding files into ISG video format."""

    def __init__(self, parent, encoder, get_progress_bar):
        """Initialize the Encode tab.

        Args:
            parent: Parent CTk widget (tab container).
            encoder: core.Encoder instance.
            get_progress_bar: Callable returning the progress bar widget.
        """
        super().__init__(parent, fg_color="transparent")
        self.encoder = encoder
        self.get_progress_bar = get_progress_bar
        self._file_path = None

        self._build_ui()

    def _build_ui(self):
        """Construct all UI elements for the encode tab."""
        # --- Input file section ---
        input_frame = ctk.CTkFrame(self)
        input_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(
            input_frame,
            text="Archivo de Entrada:",
            font=("Arial", 12, "bold"),
        ).pack(anchor="w", padx=10, pady=(10, 0))

        self.file_entry = ctk.CTkEntry(
            input_frame, placeholder_text="Ningún archivo seleccionado..."
        )
        self.file_entry.pack(side="left", fill="x", expand=True, padx=10, pady=10)

        ctk.CTkButton(
            input_frame, text="Examinar", width=100, command=self._select_file
        ).pack(side="right", padx=10, pady=10)

        # --- Encoder selection ---
        config_frame = ctk.CTkFrame(self)
        config_frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(config_frame, text="Encoder:", font=("Arial", 12)).pack(
            side="left", padx=10, pady=10
        )

        self.encoder_option = ctk.CTkOptionMenu(
            config_frame,
            values=["CPU (libx264)", "NVIDIA", "AMD", "Intel"],
        )
        self.encoder_option.pack(side="left", padx=10, pady=10)

        # --- Start button ---
        self.btn_encode = ctk.CTkButton(
            self,
            text="INICIAR CODIFICACIÓN",
            height=50,
            font=("Arial", 14, "bold"),
            fg_color="#2CC985",
            hover_color="#229A65",
            text_color="white",
            command=self._start_encoding,
        )
        self.btn_encode.pack(fill="x", padx=10, pady=20)

    def _select_file(self):
        """Open file dialog to select the input file."""
        path = filedialog.askopenfilename()
        if path:
            self._file_path = path
            self.file_entry.delete(0, "end")
            self.file_entry.insert(0, os.path.basename(path))

    def _start_encoding(self):
        """Validate and start the encoding process in a background thread."""
        if not self._file_path:
            messagebox.showerror("Error", "Selecciona un archivo primero")
            return

        output = filedialog.asksaveasfilename(
            defaultextension=".mp4",
            filetypes=[("MP4 Video", "*.mp4")],
        )
        if not output:
            return

        self.btn_encode.configure(state="disabled")
        p_bar = self.get_progress_bar()
        if p_bar:
            p_bar.set(0)

        threading.Thread(
            target=self.encoder.encode,
            args=(
                self._file_path,
                output,
                1920,
                1080,
                4,
                24,
                self.encoder_option.get(),
            ),
            daemon=True,
        ).start()

    def set_state(self, state: str):
        """Enable or disable the encode button."""
        self.btn_encode.configure(state=state)
