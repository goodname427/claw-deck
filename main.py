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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ClawDeck")


class Plugin:
    """ClawDeck Decky plugin backend"""

    client: OpenClawClient = None
    config: dict = {}
    config_path: str = ""

    async def _main(self):
        """Plugin initialization - called when the plugin is loaded"""
        self.config_path = os.path.join(decky.DECKY_PLUGIN_SETTINGS_DIR, "config.json")
        self._load_config()
        self.client = OpenClawClient(
            http_url=self.config.get("http_url", "http://localhost:18789"),
            ws_url=self.config.get("ws_url", "ws://localhost:18789/ws")
        )
        logger.info("ClawDeck plugin loaded, OpenClaw target: %s", self.config.get("http_url"))

    async def _unload(self):
        """Plugin cleanup - called when the plugin is unloaded"""
        if self.client:
            await self.client.close()
        logger.info("ClawDeck plugin unloaded")

    # ------ Public API (callable from frontend) ------

    async def send_message(self, message: str, session_key: str = "steamdeck:user") -> dict:
        """
        Send a message to OpenClaw and return the response.
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

    async def check_connection(self) -> dict:
        """
        Check if OpenClaw Gateway is reachable.
        @return dict with 'connected' bool
        """
        if not self.client:
            return {"connected": False}
        try:
            connected = await self.client.health_check()
            return {"connected": connected}
        except Exception as e:
            logger.error("Connection check failed: %s", e)
            return {"connected": False}

    async def get_config(self) -> dict:
        """
        Return current plugin configuration.
        @return dict with ws_url and http_url
        """
        return {
            "ws_url": self.config.get("ws_url", "ws://localhost:18789/ws"),
            "http_url": self.config.get("http_url", "http://localhost:18789"),
        }

    async def set_config(self, http_url: str, ws_url: str) -> dict:
        """
        Update OpenClaw Gateway addresses and persist to disk.
        @param http_url  HTTP base URL (e.g. http://192.168.1.100:18789)
        @param ws_url    WebSocket URL (e.g. ws://192.168.1.100:18789/ws)
        @return dict with 'success' bool
        """
        self.config["http_url"] = http_url
        self.config["ws_url"] = ws_url
        self._save_config()

        # Recreate client with new URLs
        if self.client:
            await self.client.close()
        self.client = OpenClawClient(http_url=http_url, ws_url=ws_url)
        logger.info("Config updated: http=%s ws=%s", http_url, ws_url)
        return {"success": True}

    async def clear_history(self) -> dict:
        """
        Clear chat message history on the frontend side.
        Backend acknowledges the request.
        @return dict with 'success' bool
        """
        return {"success": True}

    # ------ Private helpers ------

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
                    }
                self._save_config()
        except Exception as e:
            logger.error("Failed to load config: %s", e)
            self.config = {
                "http_url": "http://localhost:18789",
                "ws_url": "ws://localhost:18789/ws",
            }

    def _save_config(self):
        """Persist config to settings directory"""
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            logger.error("Failed to save config: %s", e)
