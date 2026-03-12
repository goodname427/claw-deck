"""
OpenClaw HTTP/WebSocket client for ClawDeck plugin.
Handles communication with the OpenClaw Gateway service.

Supports:
- HTTP REST API for request-response messaging
- WebSocket for streaming token-by-token responses
- Auto-reconnect with exponential backoff
- Heartbeat / ping-pong keep-alive
- Skill listing
"""
import asyncio
import hashlib
import json
import logging
import os
import struct
import socket
import ssl
import base64
import threading
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from urllib.parse import urlparse
from typing import AsyncGenerator, Callable, Optional

logger = logging.getLogger("ClawDeck.OpenClawClient")


class WebSocketConnection:
    """
    Minimal WebSocket client built on stdlib socket.
    Implements RFC 6455 enough for text frames, ping/pong, and close.
    """

    OPCODE_TEXT = 0x1
    OPCODE_CLOSE = 0x8
    OPCODE_PING = 0x9
    OPCODE_PONG = 0xA

    def __init__(self, url: str, timeout: float = 10.0):
        """
        @param url      WebSocket URL (ws:// or wss://)
        @param timeout  Socket connect/read timeout in seconds
        """
        self.url = url
        self.timeout = timeout
        self._sock: Optional[socket.socket] = None
        self._connected = False
        self._lock = threading.Lock()

    @property
    def connected(self) -> bool:
        return self._connected

    def connect(self):
        """Perform WebSocket handshake over TCP"""
        parsed = urlparse(self.url)
        use_ssl = parsed.scheme == "wss"
        host = parsed.hostname
        port = parsed.port or (443 if use_ssl else 80)
        path = parsed.path or "/"
        if parsed.query:
            path += "?" + parsed.query

        # Create TCP socket
        raw = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        raw.settimeout(self.timeout)
        raw.connect((host, port))

        if use_ssl:
            ctx = ssl.create_default_context()
            self._sock = ctx.wrap_socket(raw, server_hostname=host)
        else:
            self._sock = raw

        # WebSocket upgrade handshake
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        handshake = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {host}:{port}\r\n"
            f"Upgrade: websocket\r\n"
            f"Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            f"Sec-WebSocket-Version: 13\r\n"
            f"\r\n"
        )
        self._sock.sendall(handshake.encode("ascii"))

        # Read response headers
        response = b""
        while b"\r\n\r\n" not in response:
            chunk = self._sock.recv(4096)
            if not chunk:
                raise ConnectionError("WebSocket handshake failed: connection closed")
            response += chunk

        status_line = response.split(b"\r\n")[0].decode("ascii")
        if "101" not in status_line:
            raise ConnectionError(f"WebSocket handshake rejected: {status_line}")

        self._connected = True
        logger.info("WebSocket connected to %s", self.url)

    def close(self):
        """Send close frame and shut down the socket"""
        if not self._sock:
            return
        try:
            self._send_frame(self.OPCODE_CLOSE, b"")
        except Exception:
            pass
        try:
            self._sock.close()
        except Exception:
            pass
        self._sock = None
        self._connected = False

    def send_text(self, text: str):
        """
        Send a text frame.
        @param text  UTF-8 text payload
        """
        self._send_frame(self.OPCODE_TEXT, text.encode("utf-8"))

    def recv_frame(self) -> tuple:
        """
        Read one WebSocket frame.
        @return (opcode, payload_bytes)
        """
        # Read 2-byte header
        header = self._recv_exact(2)
        opcode = header[0] & 0x0F
        masked = (header[1] & 0x80) != 0
        length = header[1] & 0x7F

        if length == 126:
            length = struct.unpack("!H", self._recv_exact(2))[0]
        elif length == 127:
            length = struct.unpack("!Q", self._recv_exact(8))[0]

        if masked:
            mask_key = self._recv_exact(4)
            raw = self._recv_exact(length)
            payload = bytes(b ^ mask_key[i % 4] for i, b in enumerate(raw))
        else:
            payload = self._recv_exact(length)

        # Auto-respond to ping with pong
        if opcode == self.OPCODE_PING:
            self._send_frame(self.OPCODE_PONG, payload)

        return opcode, payload

    def send_ping(self, data: bytes = b""):
        """Send a ping frame for keep-alive"""
        self._send_frame(self.OPCODE_PING, data)

    # ------ Private helpers ------

    def _send_frame(self, opcode: int, payload: bytes):
        """
        Build and send a masked WebSocket frame (client must mask).
        @param opcode   Frame opcode
        @param payload  Raw payload bytes
        """
        with self._lock:
            frame = bytearray()
            frame.append(0x80 | opcode)  # FIN + opcode

            mask_key = os.urandom(4)
            length = len(payload)

            if length < 126:
                frame.append(0x80 | length)
            elif length < 65536:
                frame.append(0x80 | 126)
                frame.extend(struct.pack("!H", length))
            else:
                frame.append(0x80 | 127)
                frame.extend(struct.pack("!Q", length))

            frame.extend(mask_key)
            masked = bytes(b ^ mask_key[i % 4] for i, b in enumerate(payload))
            frame.extend(masked)

            self._sock.sendall(bytes(frame))

    def _recv_exact(self, n: int) -> bytes:
        """
        Read exactly n bytes from socket.
        @param n  Number of bytes to read
        @return bytes buffer of length n
        """
        buf = bytearray()
        while len(buf) < n:
            chunk = self._sock.recv(n - len(buf))
            if not chunk:
                raise ConnectionError("WebSocket connection closed unexpectedly")
            buf.extend(chunk)
        return bytes(buf)


class OpenClawClient:
    """
    Client for communicating with OpenClaw Gateway.
    Supports HTTP REST API and WebSocket streaming.
    """

    # Reconnect config
    RECONNECT_DELAY_INIT = 1.0   # Initial reconnect delay (seconds)
    RECONNECT_DELAY_MAX = 30.0   # Max reconnect delay (seconds)
    HEARTBEAT_INTERVAL = 25.0    # Ping interval (seconds)

    def __init__(self, http_url: str = "http://localhost:18789", ws_url: str = "ws://localhost:18789/ws"):
        """
        @param http_url  Base HTTP URL of OpenClaw Gateway
        @param ws_url    WebSocket URL of OpenClaw Gateway for streaming
        """
        self.http_url = http_url.rstrip("/")
        self.ws_url = ws_url
        self._ws: Optional[WebSocketConnection] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._reconnect_delay = self.RECONNECT_DELAY_INIT
        self._closing = False

    # ====== HTTP REST API ======

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

    async def get_skills(self) -> list:
        """
        Fetch available skills from OpenClaw Gateway.
        @return list of skill dicts with 'name', 'description', etc.
        """
        url = f"{self.http_url}/api/v1/skills"
        req = Request(url, method="GET")
        req.add_header("Accept", "application/json")

        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self._do_request, req)
            # Normalize: expect a list or a dict with a 'skills' key
            if isinstance(result, list):
                return result
            if isinstance(result, dict) and "skills" in result:
                return result["skills"]
            return []
        except Exception as e:
            logger.error("Failed to fetch skills: %s", e)
            return []

    # ====== WebSocket Streaming ======

    async def connect_ws(self):
        """
        Establish WebSocket connection with auto-reconnect.
        Starts heartbeat task on success.
        """
        self._closing = False
        loop = asyncio.get_event_loop()
        try:
            ws = WebSocketConnection(self.ws_url, timeout=10.0)
            await loop.run_in_executor(None, ws.connect)
            self._ws = ws
            self._reconnect_delay = self.RECONNECT_DELAY_INIT
            # Start heartbeat
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            logger.info("WebSocket connection established")
        except Exception as e:
            logger.error("WebSocket connect failed: %s", e)
            raise

    async def disconnect_ws(self):
        """Gracefully close WebSocket connection and stop heartbeat"""
        self._closing = True
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            self._heartbeat_task = None
        if self._ws:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._ws.close)
            self._ws = None

    async def ensure_ws_connected(self):
        """Ensure WebSocket is connected, reconnect if needed"""
        if self._ws and self._ws.connected:
            return
        await self.connect_ws()

    async def send_message_stream(self, message: str, session_key: str = "steamdeck:user") -> AsyncGenerator[dict, None]:
        """
        Send a message via WebSocket and yield streaming response chunks.
        Each yielded dict has: {'type': 'token'|'done'|'error', 'content': str}

        @param message      User input text
        @param session_key  Session identifier
        @yield dict chunks as they arrive
        """
        await self.ensure_ws_connected()

        # Send request frame
        request_payload = json.dumps({
            "type": "chat",
            "session_key": session_key,
            "content": message,
        })
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._ws.send_text, request_payload)

        # Read streaming response frames
        while True:
            try:
                opcode, payload = await asyncio.wait_for(
                    loop.run_in_executor(None, self._ws.recv_frame),
                    timeout=90.0
                )
            except asyncio.TimeoutError:
                yield {"type": "error", "content": "Response timeout"}
                break
            except ConnectionError as e:
                yield {"type": "error", "content": str(e)}
                self._ws = None
                break

            if opcode == WebSocketConnection.OPCODE_TEXT:
                try:
                    data = json.loads(payload.decode("utf-8"))
                except json.JSONDecodeError:
                    # Plain text chunk (non-JSON streaming)
                    yield {"type": "token", "content": payload.decode("utf-8")}
                    continue

                msg_type = data.get("type", "")
                if msg_type == "token" or msg_type == "chunk":
                    yield {"type": "token", "content": data.get("content", "")}
                elif msg_type == "done" or msg_type == "complete":
                    yield {"type": "done", "content": data.get("content", "")}
                    break
                elif msg_type == "error":
                    yield {"type": "error", "content": data.get("content", data.get("message", "Unknown error"))}
                    break
                else:
                    # Unknown type, treat as token
                    yield {"type": "token", "content": data.get("content", json.dumps(data))}

            elif opcode == WebSocketConnection.OPCODE_CLOSE:
                yield {"type": "error", "content": "Connection closed by server"}
                self._ws = None
                break
            # PING/PONG handled automatically in recv_frame

    @property
    def ws_connected(self) -> bool:
        """Check if WebSocket is currently connected"""
        return self._ws is not None and self._ws.connected

    # ====== Auto-reconnect ======

    async def reconnect_ws(self):
        """
        Attempt to reconnect with exponential backoff.
        @return True if reconnected, False if gave up
        """
        if self._closing:
            return False

        logger.info("Attempting WebSocket reconnect in %.1fs...", self._reconnect_delay)
        await asyncio.sleep(self._reconnect_delay)

        try:
            await self.connect_ws()
            return True
        except Exception as e:
            logger.error("Reconnect failed: %s", e)
            # Exponential backoff
            self._reconnect_delay = min(self._reconnect_delay * 2, self.RECONNECT_DELAY_MAX)
            return False

    # ====== Close / cleanup ======

    async def close(self):
        """Cleanup all resources"""
        await self.disconnect_ws()

    # ------ Private helpers ------

    async def _heartbeat_loop(self):
        """Send periodic ping frames to keep WebSocket alive"""
        try:
            while self._ws and self._ws.connected and not self._closing:
                await asyncio.sleep(self.HEARTBEAT_INTERVAL)
                if self._ws and self._ws.connected:
                    loop = asyncio.get_event_loop()
                    try:
                        await loop.run_in_executor(None, self._ws.send_ping, b"keepalive")
                    except Exception as e:
                        logger.warning("Heartbeat ping failed: %s", e)
                        break
        except asyncio.CancelledError:
            pass

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
