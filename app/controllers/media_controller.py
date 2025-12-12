from app.services.analyzer import Analyzer
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.encoders import jsonable_encoder
from app.services.log_service import LogService
from datetime import date, datetime
from pydantic import BaseModel, Field
import json
import os
import subprocess
import tempfile


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


class VideoAnalysisResponse(BaseModel):
    """
    Output payload for `POST /analyze_video`.

    The underlying video pipeline samples frames and calls an image inference endpoint.
    This endpoint returns a minimal summary, similar to `/analyze_audio`.
    """

    classification: str = Field(..., examples=["Bonafide", "Deepfake"])
    score: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description=(
            "Mean Realism score (0..100) aggregated across up to 10 sampled frames. "
            "Higher means 'more real'."
        ),
        examples=[12.0, 55.0, 97.0],
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
        "2. Samples frames from the first seconds of the video and calls the configured image inference endpoint.\n"
        "3. Derives a classification + score.\n"
        "4. Stores a detection log entry.\n\n"
        "## Output\n"
        "Returns a minimal JSON payload:\n"
        "```json\n"
        "{\"classification\": \"Bonafide\", \"score\": 72.0}\n"
        "```"
    ),
    response_model=VideoAnalysisResponse,
    responses={200: {"description": "Classification + score."}, 502: {"description": "Upstream inference endpoint error."}},
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
        # Sample enough frames to make the final decision more stable.
        result = analyzer.analyze_video(video_data, filename=getattr(file, "filename", None), frames=10, seconds=10)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Video inference failed: {type(e).__name__}: {e}")

    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=502, detail=result["error"])

    # ---- Derive score + classification from image endpoint outputs ----
    # Endpoint output example (per frame):
    # [
    #   {"label": "Deepfake", "score": 0.54},
    #   {"label": "Realism", "score": 0.46}
    # ]
    #
    # Aggregation rule (less sensitive than max-of-one-frame):
    # - Extract the per-frame "Realism" score (0..1).
    # - Compute mean Realism score over up to 10 frames.
    # - If mean Realism >= 10 (on 0..100 scale) => Bonafide else Deepfake.
    REAL_MEAN_THRESHOLD = 10.0

    def _extract_label_to_score(output) -> dict[str, float]:
        try:
            items = output
            if isinstance(output, dict):
                # Some endpoints return {"label": "...", "score": ...} or {"outputs": [...]}
                if "outputs" in output and isinstance(output["outputs"], list):
                    items = output["outputs"]
                elif "label" in output and "score" in output:
                    items = [output]

            if not isinstance(items, list):
                return {}

            out: dict[str, float] = {}

            for it in items:
                if not isinstance(it, dict):
                    continue
                label = str(it.get("label", "")).strip()
                score = it.get("score", None)
                try:
                    score_f = float(score)
                except Exception:
                    continue

                if label:
                    out[label.strip().lower()] = score_f

            return out
        except Exception:
            return {}

    def _get_realism_score_01(label_scores: dict[str, float]) -> float | None:
        # Common label variants across image deepfake models
        for key in ("realism", "real", "bonafide", "bona fide"):
            if key in label_scores:
                s = label_scores[key]
                try:
                    return max(0.0, min(float(s), 1.0))
                except Exception:
                    return None
        return None

    frame_results = []
    if isinstance(result, dict):
        frame_results = result.get("per_frame_results") or []

    realism_scores: list[float] = []
    for fr in frame_results:
        if not isinstance(fr, dict):
            continue
        out = fr.get("output")
        label_scores = _extract_label_to_score(out)
        rs = _get_realism_score_01(label_scores)
        if rs is not None:
            realism_scores.append(rs)

    if not realism_scores:
        # Nothing parsable; avoid logging misleading score.
        raise HTTPException(status_code=502, detail="Video inference succeeded but no parsable frame scores were returned.")

    # Mean of up to 10 realism scores (0..1), then scale to 0..100.
    scores_for_mean = realism_scores[:10]
    mean_realism = sum(scores_for_mean) / float(len(scores_for_mean))
    normalized_score = max(0.0, min(mean_realism, 1.0)) * 100.0
    classification = "Bonafide" if normalized_score >= REAL_MEAN_THRESHOLD else "Deepfake"
    is_deepfake = classification == "Deepfake"

    # ---- Persist log (same pattern as audio) ----
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
    audio_data = await file.read()

    # ---- Call analyzer ----
    try:
        result = analyzer.analyze_audio(
            audio_data,
            filename=getattr(file, "filename", None),
            content_type=getattr(file, "content_type", None),
        )
    except Exception as e:
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
