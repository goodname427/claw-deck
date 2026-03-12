"""
ClawDeck - OpenClaw AI Assistant plugin for Steam Deck
Python backend entry point for Decky Loader
"""
import os
import sys
import json
import asyncio
import logging

# Decky plugin module
import decky

# Plugin-local modules
sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), "py_modules"))

from openclaw_client import OpenClawClient
from hotkey_listener import HotkeyListener
from voice_recorder import VoiceRecorder

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ClawDeck")


class Plugin:
    """ClawDeck Decky plugin backend"""

    client: OpenClawClient = None
    config: dict = {}
    config_path: str = ""
    _poll_task: asyncio.Task = None
    _hotkey_listener: HotkeyListener = None
    _hotkey_triggered: bool = False  # Flag polled by frontend
    _voice_recorder: VoiceRecorder = None
    _stream_results: dict = {}  # stream_id -> accumulated result

    async def _main(self):
        """Plugin initialization - called when the plugin is loaded"""
        self.config_path = os.path.join(decky.DECKY_PLUGIN_SETTINGS_DIR, "config.json")
        self._load_config()
        self.client = OpenClawClient(
            http_url=self.config.get("http_url", "http://localhost:18789"),
            ws_url=self.config.get("ws_url", "ws://localhost:18789/ws")
        )
        # Start background connection status polling
        self._poll_task = asyncio.create_task(self._connection_poll_loop())

        # Start hotkey listener for quick sidebar access
        self._hotkey_listener = HotkeyListener(callback=self._on_hotkey_triggered)
        await self._hotkey_listener.start()

        # Initialize voice recorder
        self._voice_recorder = VoiceRecorder(
            openclaw_http=self.config.get("http_url", "http://localhost:18789")
        )

        logger.info("ClawDeck plugin loaded, OpenClaw target: %s", self.config.get("http_url"))

    async def _unload(self):
        """Plugin cleanup - called when the plugin is unloaded"""
        if self._poll_task:
            self._poll_task.cancel()
            self._poll_task = None
        if self._hotkey_listener:
            await self._hotkey_listener.stop()
            self._hotkey_listener = None
        if self._voice_recorder and self._voice_recorder.is_recording:
            await self._voice_recorder.stop_recording()
        if self.client:
            await self.client.close()
        self._stream_results.clear()
        logger.info("ClawDeck plugin unloaded")

    # ------ Public API (callable from frontend) ------

    async def send_message(self, message: str, session_key: str = "steamdeck:user") -> dict:
        """
        Send a message to OpenClaw via HTTP and return the full response.
        @param message      User input text
        @param session_key  OpenClaw session identifier
        @return dict with 'success' bool and 'data' or 'error'
        """
        if not self.client:
            return {"success": False, "error": "Plugin not initialized"}
        try:
            result = await self.client.send_message(message, session_key)
            return {"success": True, "data": result}
        except Exception as e:
            logger.error("Failed to send message: %s", e)
            return {"success": False, "error": str(e)}

    async def send_message_stream(self, message: str, session_key: str = "steamdeck:user") -> dict:
        """
        Send a message via WebSocket and start streaming response.
        Returns a stream_id that the frontend polls with poll_stream().
        @param message      User input text
        @param session_key  OpenClaw session identifier
        @return dict with 'success', 'stream_id' or 'error'
        """
        if not self.client:
            return {"success": False, "error": "Plugin not initialized"}
        try:
            # Generate unique stream ID
            import time
            stream_id = f"stream_{int(time.time() * 1000)}"
            self._stream_results[stream_id] = {
                "chunks": [],
                "done": False,
                "error": None,
                "cursor": 0,
            }
            # Start background streaming task
            asyncio.create_task(self._stream_worker(stream_id, message, session_key))
            return {"success": True, "stream_id": stream_id}
        except Exception as e:
            logger.error("Failed to start stream: %s", e)
            return {"success": False, "error": str(e)}

    async def poll_stream(self, stream_id: str) -> dict:
        """
        Poll for new streaming chunks.
        Frontend calls this repeatedly until 'done' is True.
        @param stream_id  Stream identifier from send_message_stream
        @return dict with 'chunks' (new since last poll), 'done', 'error'
        """
        state = self._stream_results.get(stream_id)
        if not state:
            return {"chunks": [], "done": True, "error": "Stream not found"}

        cursor = state["cursor"]
        new_chunks = state["chunks"][cursor:]
        state["cursor"] = len(state["chunks"])

        result = {
            "chunks": new_chunks,
            "done": state["done"],
            "error": state["error"],
        }

        # Cleanup finished streams
        if state["done"]:
            del self._stream_results[stream_id]

        return result

    async def check_connection(self) -> dict:
        """
        Check if OpenClaw Gateway is reachable via HTTP health endpoint.
        @return dict with 'connected' bool and 'ws_connected' bool
        """
        if not self.client:
            return {"connected": False, "ws_connected": False}
        try:
            connected = await self.client.health_check()
            return {
                "connected": connected,
                "ws_connected": self.client.ws_connected,
            }
        except Exception as e:
            logger.error("Connection check failed: %s", e)
            return {"connected": False, "ws_connected": False}

    async def connect_websocket(self) -> dict:
        """
        Explicitly establish WebSocket connection for streaming.
        @return dict with 'success' bool and optional 'error'
        """
        if not self.client:
            return {"success": False, "error": "Plugin not initialized"}
        try:
            await self.client.connect_ws()
            return {"success": True}
        except Exception as e:
            logger.error("WebSocket connect failed: %s", e)
            return {"success": False, "error": str(e)}

    async def disconnect_websocket(self) -> dict:
        """
        Disconnect WebSocket connection.
        @return dict with 'success' bool
        """
        if self.client:
            await self.client.disconnect_ws()
        return {"success": True}

    async def get_skills(self) -> dict:
        """
        Fetch available OpenClaw skills.
        @return dict with 'success' bool and 'skills' list
        """
        if not self.client:
            return {"success": False, "skills": [], "error": "Plugin not initialized"}
        try:
            skills = await self.client.get_skills()
            return {"success": True, "skills": skills}
        except Exception as e:
            logger.error("Failed to fetch skills: %s", e)
            return {"success": False, "skills": [], "error": str(e)}

    async def get_config(self) -> dict:
        """
        Return current plugin configuration.
        @return dict with ws_url, http_url, and streaming preference
        """
        return {
            "ws_url": self.config.get("ws_url", "ws://localhost:18789/ws"),
            "http_url": self.config.get("http_url", "http://localhost:18789"),
            "use_streaming": self.config.get("use_streaming", False),
        }

    async def set_config(self, http_url: str, ws_url: str, use_streaming: bool = False) -> dict:
        """
        Update OpenClaw Gateway addresses and persist to disk.
        @param http_url       HTTP base URL
        @param ws_url         WebSocket URL
        @param use_streaming  Enable WebSocket streaming mode
        @return dict with 'success' bool
        """
        self.config["http_url"] = http_url
        self.config["ws_url"] = ws_url
        self.config["use_streaming"] = use_streaming
        self._save_config()

        # Recreate client with new URLs
        if self.client:
            await self.client.close()
        self.client = OpenClawClient(http_url=http_url, ws_url=ws_url)
        logger.info("Config updated: http=%s ws=%s streaming=%s", http_url, ws_url, use_streaming)
        return {"success": True}

    async def clear_history(self) -> dict:
        """
        Clear chat message history on the frontend side.
        Backend acknowledges the request.
        @return dict with 'success' bool
        """
        return {"success": True}

    async def poll_hotkey(self) -> dict:
        """
        Poll whether the hotkey combo was triggered.
        Frontend calls this periodically; returns True once then resets.
        @return dict with 'triggered' bool
        """
        triggered = self._hotkey_triggered
        if triggered:
            self._hotkey_triggered = False
        return {"triggered": triggered}

    async def voice_start(self) -> dict:
        """
        Start recording audio from the Steam Deck microphone.
        @return dict with 'success' bool
        """
        if not self._voice_recorder:
            return {"success": False, "error": "Voice recorder not initialized"}
        try:
            ok = await self._voice_recorder.start_recording()
            return {"success": ok, "error": "" if ok else "Failed to start recording (arecord not available?)"}
        except Exception as e:
            logger.error("Voice start failed: %s", e)
            return {"success": False, "error": str(e)}

    async def voice_stop(self) -> dict:
        """
        Stop recording and transcribe the audio via OpenClaw STT.
        @return dict with 'success' bool, 'text' transcribed string
        """
        if not self._voice_recorder:
            return {"success": False, "text": "", "error": "Voice recorder not initialized"}
        try:
            text = await self._voice_recorder.record_and_transcribe()
            if text:
                return {"success": True, "text": text}
            return {"success": False, "text": "", "error": "No speech detected"}
        except Exception as e:
            logger.error("Voice stop/transcribe failed: %s", e)
            return {"success": False, "text": "", "error": str(e)}

    async def voice_status(self) -> dict:
        """
        Check if currently recording.
        @return dict with 'recording' bool
        """
        recording = self._voice_recorder.is_recording if self._voice_recorder else False
        return {"recording": recording}

    # ------ Private helpers ------

    async def _on_hotkey_triggered(self):
        """
        Called by HotkeyListener when the button combo is detected.
        Sets a flag that the frontend polls to open QAM sidebar.
        """
        logger.info("Hotkey triggered — signaling frontend to open sidebar")
        self._hotkey_triggered = True

    async def _stream_worker(self, stream_id: str, message: str, session_key: str):
        """
        Background task that reads WebSocket stream and populates _stream_results.
        @param stream_id    Unique stream identifier
        @param message      User message
        @param session_key  Session key
        """
        state = self._stream_results.get(stream_id)
        if not state:
            return
        try:
            async for chunk in self.client.send_message_stream(message, session_key):
                if stream_id not in self._stream_results:
                    break  # Stream was cancelled
                state["chunks"].append(chunk)
                if chunk["type"] in ("done", "error"):
                    if chunk["type"] == "error":
                        state["error"] = chunk["content"]
                    break
        except Exception as e:
            logger.error("Stream worker error: %s", e)
            state["error"] = str(e)
        finally:
            if stream_id in self._stream_results:
                self._stream_results[stream_id]["done"] = True

    async def _connection_poll_loop(self):
        """
        Background task that periodically checks connection status.
        Attempts WebSocket reconnect if disconnected and streaming is enabled.
        """
        try:
            while True:
                await asyncio.sleep(30)
                if self.client and self.config.get("use_streaming", False):
                    if not self.client.ws_connected:
                        logger.info("WebSocket disconnected, attempting reconnect...")
                        await self.client.reconnect_ws()
        except asyncio.CancelledError:
            pass

    def _load_config(self):
        """Load config from settings directory, or create defaults"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, "r", encoding="utf-8") as f:
                    self.config = json.load(f)
            else:
                # Load defaults
                defaults_path = os.path.join(
                    os.path.dirname(os.path.realpath(__file__)), "defaults", "config.json"
                )
                if os.path.exists(defaults_path):
                    with open(defaults_path, "r", encoding="utf-8") as f:
                        self.config = json.load(f)
                else:
                    self.config = {
                        "http_url": "http://localhost:18789",
                        "ws_url": "ws://localhost:18789/ws",
                        "use_streaming": False,
                    }
                self._save_config()
        except Exception as e:
            logger.error("Failed to load config: %s", e)
            self.config = {
                "http_url": "http://localhost:18789",
                "ws_url": "ws://localhost:18789/ws",
                "use_streaming": False,
            }

    def _save_config(self):
        """Persist config to settings directory"""
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            logger.error("Failed to save config: %s", e)
