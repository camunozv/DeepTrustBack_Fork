import requests
import os
import base64
from dotenv import load_dotenv
import time
import traceback

load_dotenv()

class AudioAnalyzer:
    """
    Here must be loaded the video analysis model. The goal is to access the model through the instance
    of this class.
    """
        
    def __init__(self):
        self.api_url = os.getenv("HUGGINGFACE_API_URL")
        self.api_key = os.getenv("HUGGINGFACE_API_KEY")
        # DEBUG: show config presence (never print full key)
        try:
            masked = None
            if self.api_key:
                masked = ("*" * max(0, len(self.api_key) - 4)) + self.api_key[-4:]
            print(
                f"AudioAnalyzer.__init__ api_url_set={bool(self.api_url)} "
                f"api_key_set={bool(self.api_key)} api_key_masked={masked}"
            )
        except Exception as e:
            print(f"AudioAnalyzer.__init__ DEBUG failed: {type(e).__name__}: {e}")
        
    
    def analyze_audio(self, audio_bytes):
        # The handler expects {"inputs": <base64_encoded_audio>}
        # Encode bytes to base64 string
        try:
            n = len(audio_bytes) if audio_bytes is not None else 0
            print(f"AudioAnalyzer.analyze_audio input_bytes={n}")
        except Exception:
            pass

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
                err = "HUGGINGFACE_API_URL is not set"
                print(f"AudioAnalyzer DEBUG: {err}")
                return {"error": err}

            timeout_s = int(os.getenv("HUGGINGFACE_TIMEOUT", "60"))
            print(
                "AudioAnalyzer DEBUG request="
                f"url={self.api_url} timeout_s={timeout_s} "
                f"base64_len={len(base64_audio)} approx_json_bytes={(len(base64_audio) + 50)}"
            )

            t0 = time.time()
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=timeout_s,
            )
            dt_ms = (time.time() - t0) * 1000.0
            print(
                "AudioAnalyzer DEBUG response="
                f"status={response.status_code} elapsed_ms={dt_ms:.2f} "
                f"content_type={response.headers.get('content-type')} "
                f"content_length={response.headers.get('content-length')}"
            )

            if response.status_code >= 400:
                # HuggingFace often includes useful info in body for 5xx/4xx.
                body_preview = ""
                try:
                    body_preview = (response.text or "")[:2000]
                except Exception:
                    body_preview = "<unavailable>"
                print(f"AudioAnalyzer DEBUG error_body_preview={body_preview}")

            response.raise_for_status()
            
            # Handler returns a list [{...}]
            result = response.json()
            try:
                if isinstance(result, list) and len(result) > 0 and isinstance(result[0], dict):
                    print(f"AudioAnalyzer DEBUG json=list[0]_keys={list(result[0].keys())}")
                elif isinstance(result, dict):
                    print(f"AudioAnalyzer DEBUG json=dict_keys={list(result.keys())}")
                else:
                    print(f"AudioAnalyzer DEBUG json_type={type(result).__name__}")
            except Exception:
                pass
            if isinstance(result, list) and len(result) > 0:
                return result[0]
            return result
            
        except requests.exceptions.RequestException as e:
            # Try to surface upstream body/status if available
            try:
                resp = getattr(e, "response", None)
                if resp is not None:
                    preview = ""
                    try:
                        preview = (resp.text or "")[:2000]
                    except Exception:
                        preview = "<unavailable>"
                    print(
                        "AudioAnalyzer DEBUG RequestException with response "
                        f"status={resp.status_code} body_preview={preview}"
                    )
            except Exception:
                pass

            print(f"AudioAnalyzer DEBUG RequestException={type(e).__name__}: {e}")
            try:
                print(traceback.format_exc())
            except Exception:
                pass
            return {"error": str(e)}
