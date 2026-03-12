# ClawDeck

OpenClaw AI Assistant plugin for Steam Deck, powered by [Decky Loader](https://github.com/SteamDeckHomebrew/decky-loader).

在 Steam Deck 的 Quick Access 侧边栏中直接与 [OpenClaw](https://github.com/openclaw/openclaw) AI 对话。

## Features

- 🤖 Sidebar chat panel integrated into Decky Loader
- 🔗 Connect to OpenClaw Gateway via HTTP REST API
- 🌊 WebSocket streaming with token-by-token rendering
- 🔄 Auto-reconnect with exponential backoff & heartbeat keep-alive
- 🧩 Skill browser — view and trigger OpenClaw skills
- ⚙️ Configurable Gateway address (HTTP / WebSocket)
- 💬 Real-time connection status indicator with periodic polling
- 🎮 Hotkey combo (Steam + QAM) to instantly open sidebar
- 🎤 Voice input — tap-to-record with OpenClaw STT transcription
- 🎨 SteamOS dark theme with centralized design tokens

## Project Structure

```
ClawDeck/
├── plugin.json                  # Decky Loader plugin metadata
├── package.json                 # Frontend dependencies & scripts
├── tsconfig.json                # TypeScript configuration
├── rollup.config.js             # Frontend bundler config
├── main.py                      # Python backend entry point
├── py_modules/
│   ├── openclaw_client.py       # OpenClaw HTTP + WebSocket client
│   ├── hotkey_listener.py       # Steam Deck button combo listener (evdev)
│   └── voice_recorder.py        # Microphone capture + STT proxy
├── defaults/
│   └── config.json              # Default configuration
└── src/
    ├── index.tsx                # Plugin entry point + hotkey polling
    ├── styles/
    │   └── theme.ts             # SteamOS dark theme design tokens
    └── components/
        ├── ChatPanel.tsx        # Main chat interface (HTTP + streaming)
        ├── MessageBubble.tsx    # Message bubble with streaming cursor
        ├── SettingsPanel.tsx    # Gateway settings & WS controls
        ├── SkillList.tsx        # Skill browser & trigger panel
        └── VoiceButton.tsx      # Tap-to-record voice input button
```

## Prerequisites

- [Decky Loader](https://github.com/SteamDeckHomebrew/decky-loader) installed on Steam Deck
- [OpenClaw](https://github.com/openclaw/openclaw) Gateway running and accessible
- Node.js 18+ and pnpm (for building)

## Build

```bash
# Install dependencies
pnpm install

# Build frontend
pnpm build
```

## Install

Copy the entire `ClawDeck/` directory (with `dist/`, `main.py`, `py_modules/`, `defaults/`, `plugin.json`) to:

```
~/homebrew/plugins/ClawDeck/
```

Then restart Decky Loader or reboot Steam Deck.

## Configuration

Open the plugin sidebar → click **Settings** to configure:

| Field | Default | Description |
|-------|---------|-------------|
| HTTP URL | `http://localhost:18789` | OpenClaw Gateway HTTP endpoint |
| WebSocket URL | `ws://localhost:18789/ws` | OpenClaw Gateway WebSocket endpoint |
| Enable Streaming | `false` | Use WebSocket for token-by-token responses |

Configuration is persisted to `~/homebrew/settings/ClawDeck/config.json`.

## Backend API

The Python backend exposes the following methods to the frontend via Decky's `call()` bridge:

| Method | Parameters | Returns | Description |
|--------|-----------|---------|-------------|
| `send_message` | `message: str, session_key?: str` | `{success, data/error}` | Send chat message via HTTP |
| `send_message_stream` | `message: str, session_key?: str` | `{success, stream_id}` | Start WebSocket streaming |
| `poll_stream` | `stream_id: str` | `{chunks, done, error}` | Poll streaming chunks |
| `check_connection` | — | `{connected, ws_connected}` | Test Gateway + WS status |
| `connect_websocket` | — | `{success, error?}` | Establish WS connection |
| `disconnect_websocket` | — | `{success}` | Close WS connection |
| `get_skills` | — | `{success, skills}` | List available OpenClaw skills |
| `get_config` | — | `{http_url, ws_url, use_streaming}` | Get current config |
| `set_config` | `http_url, ws_url, use_streaming` | `{success}` | Update & persist config |
| `clear_history` | — | `{success}` | Acknowledge history clear |
| `poll_hotkey` | — | `{triggered}` | Poll for hotkey combo trigger |
| `voice_start` | — | `{success, error?}` | Start microphone recording |
| `voice_stop` | — | `{success, text, error?}` | Stop recording & transcribe via STT |
| `voice_status` | — | `{recording}` | Check if currently recording |

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | TypeScript, React (Steam SP_REACT), @decky/ui, @decky/api |
| Backend | Python 3, stdlib urllib + socket + struct (zero external dependencies) |
| Bundler | Rollup |
| Target | SteamOS 3.x (Arch Linux) |

## License

[MIT](LICENSE)
