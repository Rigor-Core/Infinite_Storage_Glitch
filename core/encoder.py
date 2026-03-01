"""File-to-video encoder for Infinite Storage Glitch.

Converts any file into a black-and-white video stream where each bit
of data is represented as a macro-pixel block. The video includes an
ISG2 header with the original filename and size for recovery.
"""

import os
import math
import json
import struct
import subprocess

import numpy as np

from core.utils import BaseProcessor, check_ffmpeg


# Codec mappings for hardware-accelerated encoding
CODEC_MAP = {
    "CPU (libx264)": ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "0"],
    "NVIDIA":        ["-c:v", "h264_nvenc", "-preset", "p1"],
    "AMD":           ["-c:v", "h264_amf"],
    "Intel":         ["-c:v", "h264_qsv"],
}


class Encoder(BaseProcessor):
    """Encodes a file into a video stream using macro-pixel binary encoding."""

    def encode(
        self,
        input_path: str,
        output_path: str,
        width: int = 1920,
        height: int = 1080,
        pixel_size: int = 4,
        fps: int = 24,
        encoder: str = "CPU (libx264)",
    ):
        """Encode a file into a video.

        Args:
            input_path: Path to the source file.
            output_path: Path for the output .mp4 video.
            width: Video width in pixels.
            height: Video height in pixels.
            pixel_size: Size of each macro-pixel block.
            fps: Frames per second.
            encoder: Encoder name key from CODEC_MAP.
        """
        self.reset()

        if not check_ffmpeg():
            self.error("FFmpeg no encontrado. Instálalo y agrégalo al PATH.")
            self.finished()
            return

        file_size = os.path.getsize(input_path)
        filename = os.path.basename(input_path)

        # Build ISG2 header with file metadata
        header = json.dumps({"filename": filename, "size": file_size}).encode("utf-8")
        full_header = b"ISG2" + struct.pack(">I", len(header)) + header

        self.log(f"Codificando: {filename}")

        cols = width // pixel_size
        rows = height // pixel_size
        bytes_per_frame = (cols * rows) // 8

        total_size = len(full_header) + file_size
        total_frames = math.ceil((total_size * 8) / (cols * rows))

        # Select codec arguments
        codec_args = CODEC_MAP.get(encoder, CODEC_MAP["CPU (libx264)"])

        command = [
            "ffmpeg", "-y",
            "-f", "rawvideo", "-vcodec", "rawvideo",
            "-s", f"{width}x{height}",
            "-pix_fmt", "gray",
            "-r", str(fps),
            "-i", "-",
        ] + codec_args + ["-pix_fmt", "yuv420p", output_path]

        process = None
        try:
            process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                bufsize=10**7,
            )

            buffer = bytearray(full_header)
            frame_idx = 0

            with open(input_path, "rb") as f:
                while True:
                    if self.should_stop:
                        process.terminate()
                        return

                    # Fill buffer to at least one frame
                    while len(buffer) < bytes_per_frame:
                        chunk = f.read(1024 * 1024)
                        if not chunk:
                            break
                        buffer.extend(chunk)

                    if len(buffer) == 0:
                        break

                    # Process complete frames
                    while len(buffer) >= bytes_per_frame:
                        frame_data = buffer[:bytes_per_frame]
                        buffer = buffer[bytes_per_frame:]

                        frame_img = self._bits_to_frame(frame_data, rows, cols, pixel_size)
                        try:
                            process.stdin.write(frame_img)
                        except BrokenPipeError:
                            break

                        frame_idx += 1
                        if frame_idx % 50 == 0:
                            self.progress(
                                frame_idx / total_frames,
                                f"Frame {frame_idx}/{total_frames}",
                            )

                    # Handle remaining partial frame at EOF
                    if len(buffer) > 0 and f.tell() >= file_size:
                        frame_img = self._bits_to_frame_padded(
                            buffer, rows, cols, pixel_size
                        )
                        process.stdin.write(frame_img)
                        buffer = bytearray()
                        break

            process.stdin.close()
            process.wait()
            self.success(f"Video creado:\n{output_path}")

        except Exception as e:
            self.error(f"Error de codificación: {e}")
        finally:
            if process and process.poll() is None:
                process.terminate()
            self.finished()

    @staticmethod
    def _bits_to_frame(
        data: bytes, rows: int, cols: int, pixel_size: int
    ) -> bytes:
        """Convert raw bytes to a grayscale video frame."""
        bits = np.unpackbits(np.frombuffer(data, dtype=np.uint8))
        grid = bits.reshape((rows, cols))
        frame = grid.repeat(pixel_size, axis=0).repeat(pixel_size, axis=1)
        return ((1 - frame) * 255).astype(np.uint8).tobytes()

    @staticmethod
    def _bits_to_frame_padded(
        data: bytes, rows: int, cols: int, pixel_size: int
    ) -> bytes:
        """Convert raw bytes to a frame, padding with zeros if needed."""
        bits = np.unpackbits(np.frombuffer(bytes(data), dtype=np.uint8))
        total_bits = cols * rows
        if len(bits) < total_bits:
            bits = np.pad(bits, (0, total_bits - len(bits)), "constant")
        grid = bits[:total_bits].reshape((rows, cols))
        frame = grid.repeat(pixel_size, axis=0).repeat(pixel_size, axis=1)
        return ((1 - frame) * 255).astype(np.uint8).tobytes()
