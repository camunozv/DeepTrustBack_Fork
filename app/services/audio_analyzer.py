import requests
import os
import base64
from dotenv import load_dotenv
import shutil
import subprocess

load_dotenv()

class AudioAnalyzer:
    """
    Here must be loaded the video analysis model. The goal is to access the model through the instance
    of this class.
    """
        
    def __init__(self):
        self.api_url = os.getenv("HUGGINGFACE_AUDIO_API_URL")
        self.api_key = os.getenv("HUGGINGFACE_API_KEY")
        # DEBUG: show config presence (never print full key)
        if not self.api_key:
            raise ValueError("HUGGINGFACE_API_KEY is not set")
        if not self.api_url:
            raise ValueError("HUGGINGFACE_AUDIO_API_URL is not set")
        
    
    @staticmethod
    def _looks_like_wav(file_bytes: bytes) -> bool:
        try:
            return bool(file_bytes) and file_bytes.startswith(b"RIFF") and file_bytes[8:12] == b"WAVE"
        except Exception:
            return False

    @staticmethod
    def _looks_like_webm(file_bytes: bytes) -> bool:
        # EBML header (WebM/Matroska container)
        try:
            return bool(file_bytes) and file_bytes.startswith(b"\x1a\x45\xdf\xa3")
        except Exception:
            return False

    @staticmethod
    def _ext_from_filename(filename: str | None) -> str:
        try:
            if not filename:
                return ""
            return (os.path.splitext(filename)[1] or "").lower().lstrip(".")
        except Exception:
            return ""

    def _convert_to_wav_bytes(self, audio_bytes: bytes, input_ext: str = "", content_type: str = ""):
        """
        Convert arbitrary audio container/codec to WAV using ffmpeg.
        Uses stdin/stdout pipes (no temp files). Returns bytes or {"error": "..."}.
        """
        if not audio_bytes:
            return audio_bytes

        if self._looks_like_wav(audio_bytes):
            return audio_bytes

        ffmpeg_path = shutil.which("ffmpeg")
        if not ffmpeg_path:
            return {"error": "ffmpeg is required to convert non-wav audio (e.g. webm) but was not found in PATH"}

        # Many anti-spoof models expect mono PCM WAV at a fixed sample rate.
        # Make it configurable; keep sane defaults.
        target_sr = int(os.getenv("AUDIO_TARGET_SAMPLE_RATE", "16000"))
        target_ch = int(os.getenv("AUDIO_TARGET_CHANNELS", "1"))

        # ffmpeg auto-detects input format from the container/codec; extension is just for debug.
        cmd = [
            ffmpeg_path,
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            "pipe:0",
            "-f",
            "wav",
            "-acodec",
            "pcm_s16le",
            "-ac",
            str(target_ch),
            "-ar",
            str(target_sr),
            "pipe:1",
        ]

        try:
            p = subprocess.run(
                cmd,
                input=audio_bytes,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            if p.returncode != 0:
                err = (p.stderr or b"").decode("utf-8", errors="replace")[:2000]
                return {"error": f"ffmpeg conversion failed (exit={p.returncode}): {err}"}

            wav_bytes = p.stdout or b""
            if not self._looks_like_wav(wav_bytes):
                return {"error": "ffmpeg conversion produced non-wav output (unexpected)"}

            return wav_bytes
        except Exception as e:
            return {"error": f"ffmpeg conversion exception: {type(e).__name__}: {e}"}

    def analyze_audio(self, audio_bytes, filename: str | None = None, content_type: str | None = None):
        # The handler expects {"inputs": <base64_encoded_audio>}
        # Encode bytes to base64 string
        # Convert to wav if needed (webm uploads from browsers commonly contain Opus audio).
        try:
            ext = self._ext_from_filename(filename)
            ct = (content_type or "").lower().strip()
            should_convert = False
            if audio_bytes and not self._looks_like_wav(audio_bytes):
                if ext and ext != "wav":
                    should_convert = True
                elif ct and ("webm" in ct or "ogg" in ct or "opus" in ct or "mp3" in ct or "mp4" in ct or "m4a" in ct):
                    should_convert = True
                elif self._looks_like_webm(audio_bytes):
                    should_convert = True

            if should_convert:
                converted = self._convert_to_wav_bytes(audio_bytes or b"", input_ext=ext, content_type=ct)
                if isinstance(converted, dict) and "error" in converted:
                    return converted
                audio_bytes = converted
        except Exception as e:
            return {"error": f"audio pre-processing failed: {type(e).__name__}: {e}"}

        base64_audio = base64.b64encode(audio_bytes or b"").decode('utf-8')
        
        payload = {
            "inputs": base64_audio
        }

        headers = {
            "Accept" : "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        try:
            if not self.api_url:
                err = "HUGGINGFACE_AUDIO_API_URL is not set"
                return {"error": err}

            timeout_s = int(os.getenv("HUGGINGFACE_TIMEOUT", "60"))
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=timeout_s,
            )

            response.raise_for_status()
            
            # Handler returns a list [{...}]
            result = response.json()
            if isinstance(result, list) and len(result) > 0:
                return result[0]
            return result
            
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}
