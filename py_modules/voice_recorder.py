"""
Voice input handler for ClawDeck.
Records audio from Steam Deck microphone and sends it to OpenClaw for
speech-to-text transcription.

Uses Linux ALSA `arecord` command (available on SteamOS) for audio capture,
then POSTs the WAV data to OpenClaw's STT endpoint.
"""
import asyncio
import json
import logging
import os
import tempfile
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from typing import Optional

logger = logging.getLogger("ClawDeck.Voice")

# Audio recording parameters (optimized for speech recognition)
SAMPLE_RATE = 16000
CHANNELS = 1
FORMAT = "S16_LE"
RECORD_DEVICE = "default"


class VoiceRecorder:
    """
    Manages audio recording via ALSA arecord and speech-to-text via OpenClaw.

    @param openclaw_http  Base HTTP URL of OpenClaw Gateway (e.g. http://localhost:18789)
    @param max_duration   Maximum recording duration in seconds
    """

    def __init__(self, openclaw_http: str = "http://localhost:18789", max_duration: int = 30):
        self.openclaw_http = openclaw_http.rstrip("/")
        self.max_duration = max_duration
        self._process: Optional[asyncio.subprocess.Process] = None
        self._recording = False
        self._temp_file: Optional[str] = None

    @property
    def is_recording(self) -> bool:
        return self._recording

    async def start_recording(self) -> bool:
        """
        Start recording audio from microphone via arecord.
        @return True if recording started successfully
        """
        if self._recording:
            logger.warning("Already recording")
            return False

        # Create temp file for WAV output
        fd, self._temp_file = tempfile.mkstemp(suffix=".wav", prefix="clawdeck_voice_")
        os.close(fd)

        try:
            self._process = await asyncio.create_subprocess_exec(
                "arecord",
                "-D", RECORD_DEVICE,
                "-f", FORMAT,
                "-r", str(SAMPLE_RATE),
                "-c", str(CHANNELS),
                "-d", str(self.max_duration),
                "-t", "wav",
                self._temp_file,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            self._recording = True
            logger.info("Voice recording started: %s", self._temp_file)
            return True
        except FileNotFoundError:
            logger.error("arecord not found — voice input unavailable")
            self._cleanup_temp()
            return False
        except Exception as e:
            logger.error("Failed to start recording: %s", e)
            self._cleanup_temp()
            return False

    async def stop_recording(self) -> Optional[str]:
        """
        Stop recording and return the path to the WAV file.
        @return path to recorded WAV file, or None on failure
        """
        if not self._recording or not self._process:
            return None

        try:
            # Send SIGTERM to arecord to stop gracefully
            self._process.terminate()
            await asyncio.wait_for(self._process.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            self._process.kill()
            await self._process.wait()
        except Exception as e:
            logger.error("Error stopping recording: %s", e)

        self._recording = False
        self._process = None
        logger.info("Voice recording stopped")

        # Verify file exists and has content
        if self._temp_file and os.path.exists(self._temp_file):
            size = os.path.getsize(self._temp_file)
            if size > 44:  # WAV header is 44 bytes; need actual audio data
                return self._temp_file

        logger.warning("Recording file empty or missing")
        self._cleanup_temp()
        return None

    async def transcribe(self, wav_path: str) -> str:
        """
        Send WAV audio to OpenClaw STT endpoint for transcription.
        @param wav_path  Path to the WAV file to transcribe
        @return Transcribed text string, or empty on failure
        """
        url = f"{self.openclaw_http}/api/v1/voice/transcribe"

        try:
            with open(wav_path, "rb") as f:
                audio_data = f.read()

            # Build multipart/form-data request
            boundary = "----ClawDeckVoiceBoundary"
            body = (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="audio"; filename="voice.wav"\r\n'
                f"Content-Type: audio/wav\r\n"
                f"\r\n"
            ).encode("utf-8") + audio_data + f"\r\n--{boundary}--\r\n".encode("utf-8")

            req = Request(url, data=body, method="POST")
            req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
            req.add_header("Accept", "application/json")

            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self._do_request, req)

            # Extract transcription text from response
            if isinstance(result, dict):
                return result.get("text", result.get("transcription", ""))
            return str(result)

        except Exception as e:
            logger.error("Transcription failed: %s", e)
            return ""
        finally:
            # Cleanup temp file after transcription
            self._cleanup_temp()

    async def record_and_transcribe(self) -> str:
        """
        Convenience method: stop current recording and immediately transcribe.
        @return Transcribed text, or empty string on failure
        """
        wav_path = await self.stop_recording()
        if not wav_path:
            return ""
        return await self.transcribe(wav_path)

    def _cleanup_temp(self):
        """Remove temporary WAV file"""
        if self._temp_file and os.path.exists(self._temp_file):
            try:
                os.unlink(self._temp_file)
            except Exception:
                pass
        self._temp_file = None

    @staticmethod
    def _do_request(req: Request) -> dict:
        """
        Execute HTTP request synchronously and parse JSON.
        @param req  urllib Request object
        @return parsed JSON dict
        """
        try:
            with urlopen(req, timeout=30) as resp:
                body = resp.read().decode("utf-8")
                return json.loads(body)
        except HTTPError as e:
            body = e.read().decode("utf-8") if e.fp else ""
            raise RuntimeError(f"STT API error ({e.code}): {body}") from e
        except URLError as e:
            raise RuntimeError(f"Cannot reach STT endpoint: {e.reason}") from e
