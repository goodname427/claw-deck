"""
OpenClaw HTTP/WebSocket client for ClawDeck plugin.
Handles communication with the OpenClaw Gateway service.
"""
import asyncio
import json
import logging
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

logger = logging.getLogger("ClawDeck.OpenClawClient")


class OpenClawClient:
    """
    Client for communicating with OpenClaw Gateway.
    Supports HTTP REST API for request-response messaging.
    """

    def __init__(self, http_url: str = "http://localhost:18789", ws_url: str = "ws://localhost:18789/ws"):
        """
        @param http_url  Base HTTP URL of OpenClaw Gateway
        @param ws_url    WebSocket URL of OpenClaw Gateway (reserved for future streaming)
        """
        self.http_url = http_url.rstrip("/")
        self.ws_url = ws_url

    async def send_message(self, message: str, session_key: str = "steamdeck:user") -> dict:
        """
        Send a chat message to OpenClaw via HTTP POST.
        @param message      The user's text input
        @param session_key  Session identifier for conversation context
        @return dict containing the AI response
        """
        url = f"{self.http_url}/api/v1/chat/send"
        payload = json.dumps({
            "session_key": session_key,
            "content": message,
        }).encode("utf-8")

        req = Request(url, data=payload, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("Accept", "application/json")

        # Run blocking I/O in executor to avoid blocking the event loop
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, self._do_request, req)
        return response

    async def health_check(self) -> bool:
        """
        Check if the OpenClaw Gateway is reachable.
        @return True if gateway responds, False otherwise
        """
        url = f"{self.http_url}/api/v1/health"
        req = Request(url, method="GET")
        req.add_header("Accept", "application/json")

        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self._do_health_request, req)
            return result
        except Exception:
            return False

    async def close(self):
        """Cleanup resources (reserved for future WebSocket connection)"""
        pass

    # ------ Private helpers ------

    def _do_request(self, req: Request) -> dict:
        """
        Execute an HTTP request synchronously and parse JSON response.
        @param req  urllib Request object
        @return parsed JSON response as dict
        """
        try:
            with urlopen(req, timeout=60) as resp:
                body = resp.read().decode("utf-8")
                return json.loads(body)
        except HTTPError as e:
            body = e.read().decode("utf-8") if e.fp else ""
            logger.error("HTTP %d: %s", e.code, body)
            raise RuntimeError(f"OpenClaw API error ({e.code}): {body}") from e
        except URLError as e:
            logger.error("Connection error: %s", e.reason)
            raise RuntimeError(f"Cannot reach OpenClaw Gateway: {e.reason}") from e

    def _do_health_request(self, req: Request) -> bool:
        """
        Execute a health check request synchronously.
        @param req  urllib Request object
        @return True if status 200
        """
        try:
            with urlopen(req, timeout=5) as resp:
                return resp.status == 200
        except Exception:
            return False
