import base64
import os
import random
import tempfile
import time
import traceback
# from datetime import datetime
# from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()


class VideoAnalyzer:
    """
    Video analyzer pipeline:
    - Accepts video input as bytes (raw file bytes) OR a base64-encoded string/bytes.
    - Restricts analysis to the first N seconds (default: 10s).
    - Randomly samples K frames (default: 10) from that window.
    - Sends each sampled frame (PNG base64) to an image inference endpoint.
    """

    def __init__(self):
        self.api_url = os.getenv("HUGGINGFACE_IMAGE_API_URL")
        self.api_key = os.getenv("HUGGINGFACE_API_KEY")

        # DEBUG: show config presence (never print full key)
        if not self.api_key:
            raise ValueError("HUGGINGFACE_API_KEY is not set")
        if not self.api_url:
            raise ValueError("HUGGINGFACE_IMAGE_API_URL is not set")

    @staticmethod
    def _coerce_video_bytes(video_input) -> bytes:
        """
        Accept:
        - raw bytes (mp4/webm/etc)
        - base64 string
        - base64-as-bytes (utf-8)
        """
        if video_input is None:
            return b""

        # If it's already bytes, try to see if it's base64-as-bytes; otherwise return as-is.
        if isinstance(video_input, (bytes, bytearray)):
            b = bytes(video_input)
            try:
                s = b.decode("utf-8").strip()
            except Exception:
                return b
            try:
                # validate=True prevents silently decoding non-base64 bytes
                decoded = base64.b64decode(s, validate=True)
                return decoded if decoded else b
            except Exception:
                return b

        # If it's a string, treat as base64.
        if isinstance(video_input, str):
            s = video_input.strip()
            try:
                decoded = base64.b64decode(s, validate=True)
                return decoded if decoded else b""
            except Exception:
                # Not base64; return bytes of the string (best-effort)
                return s.encode("utf-8", errors="ignore")

        # Unknown type
        return b""

    def _headers(self) -> dict:
        return {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _query_image_endpoint(self, base64_png: str) -> dict:
        payload = {"inputs": base64_png, "parameters": {}}
        timeout_s = int(os.getenv("HUGGINGFACE_TIMEOUT", "60"))
        response = requests.post(
            self.api_url,
            headers=self._headers(),
            json=payload,
            timeout=timeout_s,
        )
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _safe_name(s: str) -> str:
        s = (s or "").strip()
        if not s:
            return "video"
        # keep letters, digits, dot, dash, underscore; replace others with "_"
        out = []
        for ch in s:
            if ch.isalnum() or ch in (".", "-", "_"):
                out.append(ch)
            else:
                out.append("_")
        return "".join(out).strip("._") or "video"

    # NOTE: temp frame extraction is disabled for now.
    # @staticmethod
    # def _project_root() -> Path:
    #     # app/services/video_analyzer.py -> app -> repo root
    #     return Path(__file__).resolve().parents[2]

    def analyze_video(self, video_input, *, filename: str | None = None, seconds: int = 10, frames: int = 10) -> dict:
        """
        Returns a dict with:
        - sampled_frame_indices
        - per_frame_results (list)
        - errors (list)
        - metadata (fps, limit_frames, etc.)
        """
        try:
            n_in = len(video_input) if isinstance(video_input, (bytes, bytearray)) else None
            print(f"VideoAnalyzer.analyze_video input_type={type(video_input).__name__} input_bytes={n_in}")
        except Exception:
            pass

        if not self.api_url:
            err = "HUGGINGFACE_IMAGE_API_URL is not set"
            print(f"VideoAnalyzer DEBUG: {err}")
            return {"error": err}

        video_bytes = self._coerce_video_bytes(video_input)
        if not video_bytes:
            return {"error": "Empty video payload"}

        # Import cv2 lazily so the service can still boot without it in non-video paths.
        try:
            import cv2  # type: ignore
        except Exception as e:
            return {"error": f"Missing dependency for video decoding: cv2 ({type(e).__name__}: {e})"}

        errors = []
        per_frame_results = []
        sampled_indices = []

        # Write to a temp file so OpenCV can decode it reliably.
        # Suffix is best-effort; OpenCV usually detects by container.
        with tempfile.NamedTemporaryFile(prefix="deeptrust_video_", suffix=".mp4", delete=True) as tmp:
            tmp.write(video_bytes)
            tmp.flush()

            cap = cv2.VideoCapture(tmp.name)
            if not cap.isOpened():
                return {"error": "Failed to open video (unsupported codec/container?)"}

            try:
                # Avoid random seeks on VP9/WebM: seeking to non-keyframes causes
                # "[vp9] Not all references are available" warnings and sometimes invalid frames.
                # Instead, read sequentially through the first `seconds` and reservoir-sample `frames`.

                # Try to use POS_MSEC to enforce the time window; it's more reliable than FPS metadata.
                max_ms = int(max(1, seconds) * 1000)
                k = max(1, int(frames))

                sampled = []  # list[tuple[frame_index, frame_bgr]]
                seen = 0
                frame_index = 0

                while True:
                    ok, frame = cap.read()
                    if not ok or frame is None:
                        break

                    # CAP_PROP_POS_MSEC is "timestamp of the *current* position".
                    # After cap.read(), this should represent the frame just grabbed.
                    pos_ms = cap.get(cv2.CAP_PROP_POS_MSEC) or 0.0
                    if pos_ms >= max_ms:
                        break

                    seen += 1
                    if len(sampled) < k:
                        sampled.append((frame_index, frame))
                    else:
                        # Reservoir sampling: replace existing with decreasing probability.
                        j = random.randrange(seen)
                        if j < k:
                            sampled[j] = (frame_index, frame)

                    frame_index += 1

                if not sampled:
                    return {"error": "No frames available in the first time window"}

                # ---- TEMP FRAME EXTRACTION (DISABLED) ----
                # If you want to re-enable saving sampled frames locally, uncomment this block.
                #
                # ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                # video_name = self._safe_name(os.path.splitext(os.path.basename(filename or "video"))[0])
                # frames_dir = self._project_root() / "temp_files" / video_name / ts
                # try:
                #     frames_dir.mkdir(parents=True, exist_ok=True)
                # except Exception as e:
                #     errors.append({"error": f"Failed to create frames dir: {type(e).__name__}: {e}", "dir": str(frames_dir)})
                #     frames_dir = None

                # Keep output stable: sort by frame index
                sampled.sort(key=lambda t: t[0])
                sampled_indices = [i for (i, _) in sampled]

                print(
                    "VideoAnalyzer DEBUG sampling="
                    f"seconds={seconds} sampled={sampled_indices} "
                    f"frames_seen_in_window={seen}"
                )

                for idx, frame in sampled:
                    try:
                        # ---- TEMP FRAME EXTRACTION (DISABLED) ----
                        # if frames_dir is not None:
                        #     try:
                        #         out_path = frames_dir / f"frame_{int(idx)}.png"
                        #         ok_write = cv2.imwrite(str(out_path), frame)
                        #         if not ok_write:
                        #             errors.append({"frame_index": idx, "error": "Failed to write frame to disk", "path": str(out_path)})
                        #     except Exception as e:
                        #         errors.append({"frame_index": idx, "error": f"Failed to save frame: {type(e).__name__}: {e}"})

                        ok_enc, buf = cv2.imencode(".png", frame)
                        if not ok_enc:
                            errors.append({"frame_index": idx, "error": "Failed to encode frame as PNG"})
                            continue

                        b64_png = base64.b64encode(buf.tobytes()).decode("utf-8")

                        t0 = time.time()
                        out = self._query_image_endpoint(b64_png)
                        dt_ms = (time.time() - t0) * 1000.0

                        per_frame_results.append(
                            {
                                "frame_index": idx,
                                "elapsed_ms": dt_ms,
                                "output": out,
                            }
                        )
                    except requests.exceptions.RequestException as e:
                        preview = None
                        try:
                            resp = getattr(e, "response", None)
                            if resp is not None:
                                preview = (resp.text or "")[:2000]
                        except Exception:
                            preview = None
                        errors.append(
                            {
                                "frame_index": idx,
                                "error": f"Image inference failed: {type(e).__name__}: {e}",
                                "upstream_body_preview": preview,
                            }
                        )
                    except Exception as e:
                        errors.append(
                            {
                                "frame_index": idx,
                                "error": f"Unexpected error: {type(e).__name__}: {e}",
                                "traceback": traceback.format_exc()[:4000],
                            }
                        )
            finally:
                try:
                    cap.release()
                except Exception:
                    pass

        return {
            "sampled_frame_indices": sampled_indices,
            "per_frame_results": per_frame_results,
            "errors": errors,
            "metadata": {
                "seconds_window": int(seconds),
                "requested_frames": int(frames),
                "returned_frames": int(len(per_frame_results)),
                # "saved_frames_dir": str(frames_dir) if "frames_dir" in locals() and frames_dir is not None else None,
            },
        }