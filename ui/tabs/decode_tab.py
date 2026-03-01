"""Decode tab UI component.

Provides the interface for selecting an ISG-encoded video,
choosing an output folder, and recovering the original file.
"""

import os
import threading

import customtkinter as ctk
from tkinter import filedialog, messagebox


class DecodeTab(ctk.CTkFrame):
    """Tab for decoding ISG videos back to the original files."""

    def __init__(self, parent, decoder, get_progress_bar):
        """Initialize the Decode tab.

        Args:
            parent: Parent CTk widget (tab container).
            decoder: core.Decoder instance.
            get_progress_bar: Callable returning the progress bar widget.
        """
        super().__init__(parent, fg_color="transparent")
        self.decoder = decoder
        self.get_progress_bar = get_progress_bar
        self._video_path = None
        self._output_folder = os.getcwd()

        self._build_ui()

    def _build_ui(self):
        """Construct all UI elements for the decode tab."""
        # --- Video file selection ---
        input_frame = ctk.CTkFrame(self)
        input_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(
            input_frame,
            text="Video Glitch:",
            font=("Arial", 12, "bold"),
        ).pack(anchor="w", padx=10, pady=(10, 0))

        self.vid_entry = ctk.CTkEntry(
            input_frame, placeholder_text="Selecciona el video..."
        )
        self.vid_entry.pack(fill="x", padx=10, pady=(5, 10))

        ctk.CTkButton(
            input_frame, text="Buscar Video", command=self._select_video
        ).pack(anchor="e", padx=10, pady=(0, 10))

        # --- Output folder selection ---
        self.btn_folder = ctk.CTkButton(
            self,
            text="📂 Seleccionar Carpeta de Salida",
            fg_color="transparent",
            border_width=2,
            text_color=("gray10", "#DCE4EE"),
            command=self._select_folder,
        )
        self.btn_folder.pack(fill="x", padx=10, pady=5)

        # --- Decode button ---
        self.btn_decode = ctk.CTkButton(
            self,
            text="RECUPERAR ARCHIVOS",
            height=50,
            font=("Arial", 14, "bold"),
            fg_color="#3B8ED0",
            hover_color="#36719F",
            command=self._start_decoding,
        )
        self.btn_decode.pack(fill="x", padx=10, pady=20)

    def _select_video(self):
        """Open file dialog to select the video file."""
        path = filedialog.askopenfilename(
            filetypes=[("Video files", "*.mp4 *.avi *.mkv")]
        )
        if path:
            self._video_path = path
            self.vid_entry.delete(0, "end")
            self.vid_entry.insert(0, os.path.basename(path))

    def _select_folder(self):
        """Open directory dialog to select the output folder."""
        folder = filedialog.askdirectory()
        if folder:
            self._output_folder = folder
            self.btn_folder.configure(
                text=f"📂 Salida: {os.path.basename(folder)}"
            )

    def _start_decoding(self):
        """Validate and start the decoding process in a background thread."""
        if not self._video_path:
            messagebox.showerror("Error", "Selecciona un video")
            return

        self.btn_decode.configure(state="disabled")
        p_bar = self.get_progress_bar()
        if p_bar:
            p_bar.set(0)
            p_bar.start()

        threading.Thread(
            target=self.decoder.decode,
            args=(self._video_path, self._output_folder),
            daemon=True,
        ).start()

    def set_state(self, state: str):
        """Enable or disable the decode button."""
        self.btn_decode.configure(state=state)

    @property
    def output_folder(self) -> str:
        """Current output folder path."""
        return self._output_folder
