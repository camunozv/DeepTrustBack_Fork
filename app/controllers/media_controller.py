from app.services.analyzer import Analyzer
from fastapi import APIRouter, UploadFile, File, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from app.services.log_service import LogService
from datetime import date, datetime
from pydantic import BaseModel, Field
import hashlib
import json
import mimetypes
import os
import subprocess
import tempfile
import time
import traceback


def _sniff_media_format(file_bytes: bytes, filename: str = "", content_type: str = "") -> str:
    """
    Best-effort "what kind of audio/video is this?" detector based on:
    - provided content_type
    - filename extension
    - magic bytes
    """
    ext = (os.path.splitext(filename or "")[1] or "").lower().lstrip(".")
    head = file_bytes[:16] if isinstance(file_bytes, (bytes, bytearray)) else b""

    # Common magic numbers
    if head.startswith(b"RIFF") and file_bytes[8:12] == b"WAVE":
        magic = "wav (RIFF/WAVE)"
    elif head.startswith(b"fLaC"):
        magic = "flac"
    elif head.startswith(b"OggS"):
        magic = "ogg/opus (OggS container)"
    elif head.startswith(b"ID3"):
        magic = "mp3 (ID3 tag)"
    elif head[:2] == b"\xff\xfb" or head[:2] == b"\xff\xf3" or head[:2] == b"\xff\xf2":
        magic = "mp3 (frame sync)"
    elif head.startswith(b"\x00\x00\x00") and b"ftyp" in file_bytes[:16]:
        magic = "mp4/m4a (ISO BMFF ftyp)"
    elif head.startswith(b"\x1a\x45\xdf\xa3"):
        magic = "webm/mkv (EBML)"
    else:
        magic = "unknown"

    guessed_by_ext = ""
    if ext:
        guessed_by_ext = f"ext={ext}"

    guessed_by_mime = ""
    if content_type:
        guessed_by_mime = f"content_type={content_type}"

    return " | ".join([p for p in [magic, guessed_by_ext, guessed_by_mime] if p]) or "unknown"


def _ffprobe_summary(file_bytes: bytes, filename: str = "") -> dict:
    """
    Best-effort ffprobe metadata (if ffprobe is installed).
    Returns a dict with either {"ffprobe": <json>} or {"ffprobe_error": "..."}.
    """
    suffix = os.path.splitext(filename or "")[1] or ""
    try:
        with tempfile.NamedTemporaryFile(prefix="deeptrust_", suffix=suffix, delete=True) as tmp:
            tmp.write(file_bytes)
            tmp.flush()

            cmd = [
                "ffprobe",
                "-hide_banner",
                "-loglevel",
                "error",
                "-show_format",
                "-show_streams",
                "-of",
                "json",
                tmp.name,
            ]
            out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True)
            return {"ffprobe": json.loads(out)}
    except FileNotFoundError:
        return {"ffprobe_error": "ffprobe not installed / not in PATH"}
    except subprocess.CalledProcessError as e:
        return {"ffprobe_error": f"ffprobe failed: exit={e.returncode} output={str(e.output)[:800]}"}
    except Exception as e:
        return {"ffprobe_error": f"ffprobe unexpected error: {type(e).__name__}: {e}"}


class AudioAnalysisResponse(BaseModel):
    """
    Output payload for `POST /analyze_audio`.

    This endpoint intentionally returns a *minimal* response so the client does not need to
    understand the full inference payload.

    - **classification**: final decision label.
      - `"Bonafide"` = real/human audio
      - `"Deepfake"` = spoofed / manipulated audio
    - **score**: normalized deepfake risk score in range `0..100` derived from the model's
      raw `deepfake_score` (`0..2`).
    """

    classification: str = Field(..., examples=["Bonafide", "Deepfake"])
    score: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description=(
            "Normalized deepfake risk score (0..100). "
            "Computed from raw deepfake_score (0..2) as clamp(deepfake_score/2, 0..1) * 100."
        ),
        examples=[0.7, 45.2, 98.9],
    )

media_handler = APIRouter()

@media_handler.post(
    "/analyze_video",
    tags=["media"],
    summary="Analyze a video for deepfake signals",
    description=(
        "## Input\n"
        "- **Content-Type**: `multipart/form-data`\n"
        "- **Form field**: `file` (UploadFile)\n\n"
        "## What this endpoint does\n"
        "1. Reads the uploaded video bytes.\n"
        "2. (Planned) Sends the video to a video deepfake inference pipeline.\n"
        "3. (Planned) Stores a detection log entry.\n\n"
        "## Output\n"
        "- **Current behavior**: returns **501 Not Implemented** until video inference exists."
    ),
    responses={
        501: {"description": "Video analysis is not implemented yet."},
    },
)
async def post_video(
    file: UploadFile = File(..., description="Video file to analyze (multipart/form-data field name: `file`).")
):
    """
    Video analysis endpoint.

    - **Input**: multipart/form-data file upload (the video)
    - **Output**: (future) model inference result
    - **Current behavior**: returns 501 until video inference is implemented
    """
    
    analyzer = Analyzer()

    video_data = await file.read()
    
    try:
        result = analyzer.analyze_video(video_data)
    except NotImplementedError as e:
        # Avoid generating fake logs/results until video inference exists.
        raise HTTPException(status_code=501, detail=str(e))
            
    return jsonable_encoder(result)


@media_handler.post(
    "/analyze_audio",
    tags=["media"],
    summary="Analyze an audio clip and log the result",
    description=(
        "## Input\n"
        "- **Content-Type**: `multipart/form-data`\n"
        "- **Form field**: `file` (UploadFile)\n\n"
        "## What this endpoint does\n"
        "1. Reads the uploaded audio bytes.\n"
        "2. Calls the configured inference endpoint (via `AudioAnalyzer`).\n"
        "3. Extracts the model decision (`is_bonafide` / `label`).\n"
        "4. Normalizes the raw `deepfake_score` (0..2) into a client-friendly `score` (0..100).\n"
        "5. Saves a log entry to the `DetectionLog` table with:\n"
        "   - `classification` (\"Bonafide\" | \"Deepfake\")\n"
        "   - `score` (0..100)\n"
        "   - `date`, `hour` (server time)\n\n"
        "## Output\n"
        "Returns a minimal JSON payload:\n"
        "```json\n"
        "{\"classification\": \"Bonafide\", \"score\": 12.5}\n"
        "```\n\n"
        "## Scoring / Normalization\n"
        "- Raw `deepfake_score` is expected in range **0..2** (higher = more fake)\n"
        "- Returned `score` is computed as:\n"
        "  - `score = clamp(deepfake_score / 2, 0..1) * 100`\n"
        "  - final range: **0..100**\n\n"
        "## Classification\n"
        "- `is_bonafide=true`  → `classification=\"Bonafide\"`\n"
        "- `is_bonafide=false` → `classification=\"Deepfake\"`\n"
    ),
    response_model=AudioAnalysisResponse,
    responses={
        200: {"description": "Classification + normalized score."},
        502: {"description": "Upstream inference endpoint error."},
    },
)
async def post_audio(
    request: Request,
    file: UploadFile = File(..., description="Audio file to analyze (multipart/form-data field name: `file`).")
):
    """
    Audio analysis endpoint.

    - **Input**: multipart/form-data file upload (the audio clip)
    - **Side effects**: writes a row into the `DetectionLog` table with:
      - `classification` ("Bonafide" | "Deepfake")
      - `score` (0..100)
      - `date`, `hour` (server time)
    - **Output**: minimal JSON response with `classification` and `score`
    """
    
    analyzer = Analyzer()

    # ---- DEBUG: inbound request + file metadata ----
    try:
        print("=== /analyze_audio DEBUG (inbound) ===")
        print(f"client={getattr(request, 'client', None)} method={request.method} url={request.url}")
        # Avoid printing all headers (can be noisy); focus on the ones useful for file uploads.
        print(
            "headers_subset="
            + json.dumps(
                {
                    "content-type": request.headers.get("content-type"),
                    "content-length": request.headers.get("content-length"),
                    "user-agent": request.headers.get("user-agent"),
                    "origin": request.headers.get("origin"),
                },
                default=str,
            )
        )
        print(
            f"upload.filename={getattr(file, 'filename', None)} "
            f"upload.content_type={getattr(file, 'content_type', None)}"
        )
        if getattr(file, "filename", None):
            print(f"mimetypes.guess_type={mimetypes.guess_type(file.filename)}")
    except Exception as e:
        print(f"/analyze_audio DEBUG: failed printing inbound metadata: {type(e).__name__}: {e}")

    t0 = time.time()
    audio_data = await file.read()
    t_read = (time.time() - t0) * 1000.0

    # ---- DEBUG: bytes metadata ----
    try:
        size = len(audio_data) if audio_data is not None else 0
        sha256 = hashlib.sha256(audio_data).hexdigest() if audio_data else None
        print(f"read_bytes={size} read_ms={t_read:.2f}")
        print(f"sha256={(sha256[:16] + '…') if sha256 else None}")
        print(f"first32_hex={audio_data[:32].hex() if audio_data else None}")
        print(f"sniff_format={_sniff_media_format(audio_data or b'', file.filename or '', file.content_type or '')}")
        # ffprobe can be very helpful to diagnose 'm4a disguised as wav', etc.
        if audio_data:
            ff = _ffprobe_summary(audio_data, file.filename or "")
            # Keep output bounded; still prints most useful info.
            print(f"ffprobe_summary={json.dumps(ff, default=str)[:2000]}")
    except Exception as e:
        print(f"/analyze_audio DEBUG: failed printing bytes metadata: {type(e).__name__}: {e}")

    # ---- Call analyzer with debug ----
    try:
        t1 = time.time()
        result = analyzer.analyze_audio(audio_data)
        t_an = (time.time() - t1) * 1000.0
        print(f"analyze_audio_ms={t_an:.2f} result_type={type(result).__name__}")
        if isinstance(result, dict):
            print(f"result_keys={list(result.keys())}")
    except Exception as e:
        print("=== /analyze_audio DEBUG (exception) ===")
        print(f"exception={type(e).__name__}: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=502, detail=f"Audio inference failed: {type(e).__name__}: {e}")
    
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=502, detail=result["error"])

    # Endpoint contract:
    # - deepfake_score is in range 0..2 (higher = more fake)
    # - is_bonafide is the primary decision flag
    raw_score = float(result.get("deepfake_score", 0.0) or 0.0)
    normalized_score = max(0.0, min(raw_score / 2.0, 1.0)) * 100.0

    is_bonafide = result.get("is_bonafide", None)
    if is_bonafide is None:
        label = str(result.get("label", "")).strip().lower()
        is_bonafide = (label == "bonafide")

    classification = "Bonafide" if bool(is_bonafide) else "Deepfake"
    is_deepfake = classification == "Deepfake"  # keep boolean for backward compatibility

    log = {
        "isDeepFake": is_deepfake,
        "date": date.today(),
        "hour": datetime.now().time(),
        "classification": classification,
        "score": normalized_score,
    }
        
    log_service = LogService()
    
    log_service.save_log(log)
    
    return jsonable_encoder(
        {
            "classification": classification,
            "score": normalized_score,
        }
    )
