"""Video-to-file decoder for Infinite Storage Glitch.

Reads a video encoded by the Encoder and recovers the original file,
using batch-processing of frames for performance and the ISG2 header
for metadata recovery.
"""

import os
import json
import struct
import shutil
import subprocess

import numpy as np

from core.utils import BaseProcessor, check_ffmpeg


# Number of frames to process in a single batch for performance
BATCH_FRAMES = 60


class Decoder(BaseProcessor):
    """Decodes an ISG-encoded video back to the original file."""

    def decode(self, input_path: str, output_folder: str):
        """Decode a video file and recover the embedded file.

        Args:
            input_path: Path to the encoded video file.
            output_folder: Directory to save the recovered file.
        """
        self.reset()

        if not check_ffmpeg():
            self.error("FFmpeg no encontrado. Instálalo y agrégalo al PATH.")
            self.finished()
            return

        self.log(f"Recuperando: {os.path.basename(input_path)}")

        # Probe video dimensions
        width, height = self._probe_dimensions(input_path)
        if width is None:
            self.finished()
            return

        pixel_size = 4
        offset = pixel_size // 2

        frame_bytes = width * height
        batch_bytes = frame_bytes * BATCH_FRAMES

        temp_bin = os.path.join(output_folder, "temp_raw.bin")

        command = [
            "ffmpeg", "-y", "-i", input_path,
            "-f", "image2pipe", "-pix_fmt", "gray",
            "-vcodec", "rawvideo", "-",
        ]

        process = None
        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                bufsize=10**8,
            )

            with open(temp_bin, "wb") as f_out:
                while True:
                    if self.should_stop:
                        process.terminate()
                        return

                    raw_batch = process.stdout.read(batch_bytes)
                    if not raw_batch:
                        break

                    read_len = len(raw_batch)

                    # Pad incomplete final batch
                    if read_len % frame_bytes != 0:
                        missing = frame_bytes - (read_len % frame_bytes)
                        raw_batch += b"\x00" * missing

                    num_frames = len(raw_batch) // frame_bytes

                    # Vectorized frame processing with NumPy
                    batch_np = np.frombuffer(raw_batch, dtype=np.uint8).reshape(
                        (num_frames, height, width)
                    )
                    sampled = batch_np[:, offset::pixel_size, offset::pixel_size]
                    bits = (sampled < 128).astype(np.uint8)
                    bytes_out = np.packbits(bits).tobytes()

                    f_out.write(bytes_out)

            process.wait()

            # Recover the file from the raw binary
            self._recover_file(temp_bin, output_folder)

        except Exception as e:
            self.error(f"Error de decodificación: {e}")
        finally:
            if process and process.poll() is None:
                process.terminate()
            # Clean up temp file
            try:
                if os.path.exists(temp_bin):
                    os.remove(temp_bin)
            except OSError:
                pass
            self.finished()

    def _probe_dimensions(self, input_path: str):
        """Get video width and height using ffprobe.

        Returns:
            tuple: (width, height) or (None, None) on error.
        """
        try:
            probe = subprocess.check_output([
                "ffprobe", "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=width,height",
                "-of", "csv=p=0",
                input_path,
            ]).decode().strip().split(",")
            return int(probe[0]), int(probe[1])
        except (subprocess.CalledProcessError, ValueError, IndexError) as e:
            self.error(f"Error leyendo video: {e}")
            return None, None

    def _recover_file(self, temp_bin: str, output_folder: str):
        """Parse the ISG2 header and reconstruct the original file."""
        if not os.path.exists(temp_bin):
            self.error("No se generó el archivo temporal.")
            return

        self.log("Procesando archivo final...")

        with open(temp_bin, "rb") as f:
            magic = f.read(4)
            if magic == b"ISG2":
                try:
                    hlen_bytes = f.read(4)
                    if not hlen_bytes:
                        raise ValueError("Archivo corrupto o vacío")

                    hlen = struct.unpack(">I", hlen_bytes)[0]
                    header_data = f.read(hlen)
                    header = json.loads(header_data.decode("utf-8"))

                    real_name = header["filename"]
                    real_size = header["size"]

                    self.log(f"Archivo detectado: {real_name}")
                    final_path = os.path.join(output_folder, real_name)

                    # Write recovered data in large chunks
                    with open(final_path, "wb") as f_final:
                        while True:
                            chunk = f.read(1024 * 1024 * 5)  # 5 MB chunks
                            if not chunk:
                                break
                            f_final.write(chunk)

                    # Truncate to exact original size
                    with open(final_path, "a+b") as f_final:
                        f_final.truncate(real_size)

                    self.success(f"Recuperado: {real_name}")

                except (ValueError, KeyError, json.JSONDecodeError) as e:
                    self.error(f"Error de cabecera: {e}")
            else:
                # No ISG2 header — save as raw binary
                final_path = os.path.join(output_folder, "recuperado_raw.bin")
                shutil.copy(temp_bin, final_path)
                self.success("Recuperado sin cabecera (RAW)")
