"""
Steam Deck hotkey listener for ClawDeck.
Monitors controller/keyboard input events to trigger QAM open via a custom combo.

Uses Linux evdev (input event subsystem) to detect button combos on Steam Deck.
Falls back gracefully if evdev devices are unavailable (e.g. desktop dev environment).
"""
import asyncio
import glob
import logging
import os
import struct
import time
from typing import Callable, Optional

logger = logging.getLogger("ClawDeck.Hotkey")

# Linux input event format: struct input_event { timeval, __u16 type, __u16 code, __s32 value }
EVENT_FORMAT = "llHHi"
EVENT_SIZE = struct.calcsize(EVENT_FORMAT)

# Event types
EV_KEY = 0x01

# Key state values
KEY_RELEASE = 0
KEY_PRESS = 1

# Steam Deck controller button codes (under /dev/input/eventX)
# These map to the physical buttons on the Deck
BTN_STEAM = 0x13A        # Steam button (BTN_MODE)
BTN_QAM = 0x13B          # QAM / "..." button (BTN_START on some mappings)
BTN_QUICK_ACCESS = 0x13B  # Alias


class HotkeyListener:
    """
    Listens for a configurable button combo on Steam Deck input devices.
    When the combo is detected, fires a callback (used to open QAM sidebar).

    @param combo     Set of evdev key codes that must all be pressed simultaneously
    @param callback  Async function to call when combo is detected
    """

    # Debounce: minimum seconds between triggers
    DEBOUNCE_INTERVAL = 1.0

    def __init__(self, combo: set = None, callback: Callable = None):
        self.combo = combo or {BTN_STEAM, BTN_QAM}
        self.callback = callback
        self._pressed: set = set()
        self._task: Optional[asyncio.Task] = None
        self._running = False
        self._last_trigger = 0.0

    async def start(self):
        """Start listening for input events in background"""
        if self._running:
            return

        device_path = self._find_input_device()
        if not device_path:
            logger.warning("No suitable input device found; hotkey listener disabled")
            return

        self._running = True
        self._task = asyncio.create_task(self._listen_loop(device_path))
        logger.info("Hotkey listener started on %s, combo=%s", device_path, self.combo)

    async def stop(self):
        """Stop listening"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        self._pressed.clear()
        logger.info("Hotkey listener stopped")

    def _find_input_device(self) -> Optional[str]:
        """
        Find the most likely Steam Deck controller input device.
        Looks for devices with 'Steam Deck' or 'Valve' in their name.
        @return path to /dev/input/eventX or None
        """
        for event_dir in sorted(glob.glob("/dev/input/event*")):
            try:
                # Read device name from sysfs
                event_num = os.path.basename(event_dir)
                name_path = f"/sys/class/input/{event_num}/device/name"
                if os.path.exists(name_path):
                    with open(name_path, "r") as f:
                        name = f.read().strip().lower()
                    if "steam" in name or "valve" in name or "deck" in name:
                        return event_dir
            except Exception:
                continue

        # Fallback: try first available event device
        devices = sorted(glob.glob("/dev/input/event*"))
        if devices:
            return devices[0]
        return None

    async def _listen_loop(self, device_path: str):
        """
        Main event loop reading from evdev device.
        @param device_path  Path to /dev/input/eventX
        """
        loop = asyncio.get_event_loop()
        try:
            fd = os.open(device_path, os.O_RDONLY | os.O_NONBLOCK)
        except OSError as e:
            logger.error("Cannot open input device %s: %s", device_path, e)
            self._running = False
            return

        try:
            while self._running:
                try:
                    data = await loop.run_in_executor(None, self._read_event, fd)
                    if data is None:
                        await asyncio.sleep(0.01)
                        continue

                    _sec, _usec, ev_type, ev_code, ev_value = struct.unpack(EVENT_FORMAT, data)

                    if ev_type != EV_KEY:
                        continue

                    if ev_value == KEY_PRESS:
                        self._pressed.add(ev_code)
                    elif ev_value == KEY_RELEASE:
                        self._pressed.discard(ev_code)

                    # Check if combo is satisfied
                    if self.combo.issubset(self._pressed):
                        now = time.monotonic()
                        if now - self._last_trigger >= self.DEBOUNCE_INTERVAL:
                            self._last_trigger = now
                            logger.info("Hotkey combo detected!")
                            if self.callback:
                                await self.callback()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.debug("Event read error: %s", e)
                    await asyncio.sleep(0.05)
        finally:
            os.close(fd)

    @staticmethod
    def _read_event(fd: int) -> Optional[bytes]:
        """
        Read one input_event from file descriptor (non-blocking).
        @param fd  File descriptor for evdev device
        @return raw bytes or None if no data available
        """
        try:
            return os.read(fd, EVENT_SIZE)
        except BlockingIOError:
            return None
        except OSError:
            return None
